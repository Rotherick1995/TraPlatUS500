# src/application/use_cases/place_pending_order.py

from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
import logging

# Importación condicional para evitar dependencias circulares
if TYPE_CHECKING:
    from src.domain.repositories.abstract.order_repository import OrderRepository
    from src.application.validators.order_validator import OrderValidator


@dataclass
class PlacePendingOrderRequest:
    """Solicitud para colocar una orden pendiente."""
    
    symbol: str
    order_type: str  # 'LIMIT_BUY', 'LIMIT_SELL', 'STOP_BUY', 'STOP_SELL'
    volume: float
    price: float  # Precio de activación para la orden pendiente
    stop_loss: float = 0.0  # Nivel de Stop Loss
    take_profit: float = 0.0  # Nivel de Take Profit
    comment: str = ""
    expiration: Optional[datetime] = None  # Fecha de expiración (opcional)
    magic_number: int = 234000


@dataclass
class PlacePendingOrderResponse:
    """Respuesta de la orden pendiente colocada."""
    
    success: bool
    message: str
    ticket: Optional[int] = None
    order_type: str = ""
    price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    volume: float = 0.0
    symbol: str = ""
    expiration: Optional[str] = None
    timestamp: str = ""
    error_code: int = 0


class PlacePendingOrderUseCase:
    """Caso de uso para colocar órdenes pendientes (LIMIT/STOP)."""
    
    # Mapeo de tipos de orden pendiente
    ORDER_TYPE_MAP = {
        'LIMIT_BUY': 'buy_limit',
        'LIMIT_SELL': 'sell_limit',
        'STOP_BUY': 'buy_stop',
        'STOP_SELL': 'sell_stop'
    }
    
    def __init__(self, order_repository: "OrderRepository", order_validator: Optional["OrderValidator"] = None):
        """
        Inicializa el caso de uso para órdenes pendientes.
        
        Args:
            order_repository: Repositorio de órdenes para comunicación con MT5
            order_validator: Validador de órdenes (opcional, se creará si no se proporciona)
        """
        self.order_repository = order_repository
        self._validator = order_validator
        self.logger = logging.getLogger(__name__)
    
    @property
    def validator(self) -> "OrderValidator":
        """
        Propiedad para obtener el validador, creándolo si es necesario.
        
        Returns:
            OrderValidator: Instancia del validador
        """
        if self._validator is None:
            # Importación diferida para evitar dependencias circulares
            from src.application.validators.order_validator import OrderValidator
            self._validator = OrderValidator()
        return self._validator
    
    def execute(self, request: PlacePendingOrderRequest) -> PlacePendingOrderResponse:
        """
        Ejecuta la colocación de una orden pendiente.
        
        Args:
            request: Datos de la orden pendiente a colocar
            
        Returns:
            PlacePendingOrderResponse: Resultado de la operación
        """
        try:
            self.logger.info(f"Iniciando orden pendiente: {request.symbol} {request.order_type} a {request.price}")
            
            # 1. Validar parámetros básicos
            validation_result = self.validator.validate_pending_order_request(request)
            if not validation_result["valid"]:
                return PlacePendingOrderResponse(
                    success=False,
                    message=f"Validación fallida: {validation_result['message']}",
                    symbol=request.symbol,
                    order_type=request.order_type,
                    timestamp=datetime.now().isoformat()
                )
            
            # 2. Verificar que el precio sea válido
            if request.price <= 0:
                return PlacePendingOrderResponse(
                    success=False,
                    message="El precio de activación debe ser mayor que cero",
                    symbol=request.symbol,
                    order_type=request.order_type,
                    timestamp=datetime.now().isoformat()
                )
            
            # 3. Obtener precio actual para validaciones
            current_price = self._get_current_price(request.symbol, request.order_type)
            if current_price <= 0:
                self.logger.warning(f"No se pudo obtener precio actual para {request.symbol}")
                # Continuamos sin validación de precio, pero con advertencia
            
            # 4. Validar distancia del precio de activación
            if current_price > 0:
                price_validation = self._validate_activation_price(
                    symbol=request.symbol,
                    order_type=request.order_type,
                    activation_price=request.price,
                    current_price=current_price
                )
                if not price_validation["valid"]:
                    return PlacePendingOrderResponse(
                        success=False,
                        message=price_validation["message"],
                        symbol=request.symbol,
                        order_type=request.order_type,
                        timestamp=datetime.now().isoformat()
                    )
            
            # 5. Preparar niveles SL y TP
            sl_level, tp_level = self._prepare_sl_tp_levels(
                symbol=request.symbol,
                order_type=request.order_type,
                activation_price=request.price,
                sl_value=request.stop_loss,
                tp_value=request.take_profit
            )
            
            self.logger.debug(f"SL: {sl_level}, TP: {tp_level}")
            
            # 6. Colocar la orden pendiente en MT5
            ticket = self._place_pending_order_in_repository(
                symbol=request.symbol,
                order_type=request.order_type,
                volume=request.volume,
                price=request.price,
                stop_loss=sl_level,
                take_profit=tp_level,
                comment=request.comment,
                expiration=request.expiration
            )
            
            # 7. Verificar resultado
            if ticket:
                self.logger.info(f"✅ Orden pendiente exitosa - Ticket: {ticket}")
                
                return PlacePendingOrderResponse(
                    success=True,
                    message="Orden pendiente colocada exitosamente",
                    ticket=ticket,
                    order_type=request.order_type,
                    price=request.price,
                    stop_loss=sl_level,
                    take_profit=tp_level,
                    volume=request.volume,
                    symbol=request.symbol,
                    expiration=request.expiration.isoformat() if request.expiration else None,
                    timestamp=datetime.now().isoformat()
                )
            else:
                error_msg = self._get_last_error()
                self.logger.error(f"❌ Error al colocar orden pendiente: {error_msg}")
                
                return PlacePendingOrderResponse(
                    success=False,
                    message=f"Error al colocar orden pendiente: {error_msg}",
                    symbol=request.symbol,
                    order_type=request.order_type,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada al colocar orden pendiente: {str(e)}")
            
            return PlacePendingOrderResponse(
                success=False,
                message=f"Error inesperado: {str(e)}",
                symbol=request.symbol,
                order_type=request.order_type,
                timestamp=datetime.now().isoformat()
            )
    
    def _get_current_price(self, symbol: str, order_type: str) -> float:
        """
        Obtiene el precio actual según el tipo de orden.
        
        Args:
            symbol: Símbolo a consultar
            order_type: Tipo de orden pendiente
            
        Returns:
            float: Precio actual (bid o ask según corresponda)
        """
        try:
            # Intenta obtener el precio del repositorio si está disponible
            if hasattr(self.order_repository, 'get_symbol_info'):
                info = self.order_repository.get_symbol_info(symbol)
                # Esto es un ejemplo - ajusta según tu implementación real
                return info.get('ask', 0.0) if 'buy' in order_type.lower() else info.get('bid', 0.0)
        except (AttributeError, KeyError):
            pass
        
        # Si no se puede obtener el precio, retornar 0.0
        return 0.0
    
    def _validate_activation_price(self, symbol: str, order_type: str, 
                                   activation_price: float, current_price: float) -> Dict[str, Any]:
        """
        Valida que el precio de activación sea apropiado.
        
        Args:
            symbol: Símbolo del activo
            order_type: Tipo de orden pendiente
            activation_price: Precio de activación solicitado
            current_price: Precio actual del mercado
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        # Obtener información del símbolo
        symbol_info = self._get_symbol_info(symbol)
        point = symbol_info.get('point', 0.00001)
        
        # Distancia mínima en pips
        MIN_DISTANCE_PIPS = 10
        
        # Calcular distancia actual
        distance_pips = abs(activation_price - current_price) / point
        
        if distance_pips < MIN_DISTANCE_PIPS:
            return {
                "valid": False,
                "message": f"El precio de activación debe estar al menos a {MIN_DISTANCE_PIPS} pips del precio actual"
            }
        
        # Validar dirección según tipo de orden
        order_type_lower = order_type.lower()
        
        if 'limit' in order_type_lower:
            # Órdenes LIMIT deben estar mejor que el precio actual
            if 'buy' in order_type_lower:
                # LIMIT BUY: precio de activación debe estar POR DEBAJO del precio actual
                if activation_price >= current_price:
                    return {
                        "valid": False,
                        "message": "Para LIMIT BUY, el precio debe estar por debajo del precio actual"
                    }
            else:  # sell_limit
                # LIMIT SELL: precio de activación debe estar POR ENCIMA del precio actual
                if activation_price <= current_price:
                    return {
                        "valid": False,
                        "message": "Para LIMIT SELL, el precio debe estar por encima del precio actual"
                    }
        
        elif 'stop' in order_type_lower:
            # Órdenes STOP deben estar peor que el precio actual
            if 'buy' in order_type_lower:
                # STOP BUY: precio de activación debe estar POR ENCIMA del precio actual
                if activation_price <= current_price:
                    return {
                        "valid": False,
                        "message": "Para STOP BUY, el precio debe estar por encima del precio actual"
                    }
            else:  # sell_stop
                # STOP SELL: precio de activación debe estar POR DEBAJO del precio actual
                if activation_price >= current_price:
                    return {
                        "valid": False,
                        "message": "Para STOP SELL, el precio debe estar por debajo del precio actual"
                    }
        
        return {"valid": True, "message": "Precio válido"}
    
    def _prepare_sl_tp_levels(self, symbol: str, order_type: str, 
                             activation_price: float, sl_value: float, tp_value: float) -> Tuple[float, float]:
        """
        Prepara niveles de SL y TP para órdenes pendientes.
        
        Args:
            symbol: Símbolo del activo
            order_type: Tipo de orden pendiente
            activation_price: Precio de activación
            sl_value: Nivel de Stop Loss
            tp_value: Nivel de Take Profit
            
        Returns:
            Tuple[float, float]: (nivel_sl, nivel_tp)
        """
        if activation_price <= 0:
            return 0.0, 0.0
        
        # Si los valores son 0, retornar 0
        if sl_value == 0 and tp_value == 0:
            return 0.0, 0.0
        
        # Obtener información del símbolo
        symbol_info = self._get_symbol_info(symbol)
        point = symbol_info.get('point', 0.00001)
        
        order_type_lower = order_type.lower()
        
        # Determinar dirección de la operación
        is_buy = 'buy' in order_type_lower
        
        # Calcular niveles
        sl_level = 0.0
        tp_level = 0.0
        
        if sl_value != 0:
            if is_buy:
                # Para compras: SL por debajo del precio de activación
                sl_level = activation_price - (abs(sl_value) * point)
            else:
                # Para ventas: SL por encima del precio de activación
                sl_level = activation_price + (abs(sl_value) * point)
        
        if tp_value != 0:
            if is_buy:
                # Para compras: TP por encima del precio de activación
                tp_level = activation_price + (abs(tp_value) * point)
            else:
                # Para ventas: TP por debajo del precio de activación
                tp_level = activation_price - (abs(tp_value) * point)
        
        # Validar que SL y TP estén en la dirección correcta
        if sl_level > 0:
            if is_buy and sl_level >= activation_price:
                self.logger.warning(f"SL inválido para orden de compra: {sl_level} >= {activation_price}")
                sl_level = 0.0
            elif not is_buy and sl_level <= activation_price:
                self.logger.warning(f"SL inválido para orden de venta: {sl_level} <= {activation_price}")
                sl_level = 0.0
        
        if tp_level > 0:
            if is_buy and tp_level <= activation_price:
                self.logger.warning(f"TP inválido para orden de compra: {tp_level} <= {activation_price}")
                tp_level = 0.0
            elif not is_buy and tp_level >= activation_price:
                self.logger.warning(f"TP inválido para orden de venta: {tp_level} >= {activation_price}")
                tp_level = 0.0
        
        return sl_level, tp_level
    
    def _get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene información del símbolo.
        
        Args:
            symbol: Símbolo a consultar
            
        Returns:
            Dict[str, Any]: Información del símbolo
        """
        # Valores por defecto para símbolos comunes
        default_info = {
            'EURUSD': {'point': 0.00001, 'digits': 5, 'spread': 10},
            'US500': {'point': 0.01, 'digits': 2, 'spread': 25},
            'GBPUSD': {'point': 0.00001, 'digits': 5, 'spread': 12},
            'USDJPY': {'point': 0.001, 'digits': 3, 'spread': 8},
            'XAUUSD': {'point': 0.01, 'digits': 2, 'spread': 30}
        }
        
        return default_info.get(symbol, {'point': 0.00001, 'digits': 5, 'spread': 10})
    
    def _place_pending_order_in_repository(self, symbol: str, order_type: str, 
                                          volume: float, price: float, stop_loss: float,
                                          take_profit: float, comment: str, 
                                          expiration: Optional[datetime] = None) -> Optional[int]:
        """
        Coloca una orden pendiente utilizando el repositorio.
        
        Args:
            symbol: Símbolo del activo
            order_type: Tipo de orden pendiente
            volume: Volumen en lotes
            price: Precio de activación
            stop_loss: Nivel de Stop Loss
            take_profit: Nivel de Take Profit
            comment: Comentario para la orden
            expiration: Fecha de expiración (opcional)
            
        Returns:
            Optional[int]: Ticket de la orden o None si falla
        """
        try:
            # Convertir order_type al formato que espera el repositorio
            mt5_order_type = self.ORDER_TYPE_MAP.get(order_type, order_type)
            
            # Verificar si el repositorio tiene método para órdenes pendientes
            if hasattr(self.order_repository, 'place_pending_order'):
                ticket = self.order_repository.place_pending_order(
                    symbol=symbol,
                    order_type=mt5_order_type,
                    volume=volume,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment,
                    expiration=expiration
                )
                return ticket
            
            # Si no tiene método específico, intentar con método genérico
            elif hasattr(self.order_repository, 'place_order'):
                # Para órdenes pendientes, podríamos adaptar el método place_order
                self.logger.warning(f"Usando place_order para orden pendiente: {order_type}")
                ticket = self.order_repository.place_order(
                    symbol=symbol,
                    order_type=mt5_order_type,
                    volume=volume,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment
                )
                return ticket
            
            else:
                self.logger.error("Repositorio no tiene métodos para colocar órdenes")
                return None
                
        except Exception as e:
            self.logger.error(f"Error al colocar orden pendiente en repositorio: {str(e)}")
            return None
    
    def _get_last_error(self) -> str:
        """
        Obtiene el último error del repositorio.
        
        Returns:
            str: Mensaje de error
        """
        try:
            if hasattr(self.order_repository, 'get_last_error'):
                return self.order_repository.get_last_error()
        except Exception:
            pass
        
        return "Error desconocido"


# Factory function para crear el caso de uso
def create_place_pending_order_use_case(
    order_repository: "OrderRepository", 
    order_validator: Optional["OrderValidator"] = None
) -> PlacePendingOrderUseCase:
    """
    Crea una instancia del caso de uso para órdenes pendientes.
    
    Args:
        order_repository: Repositorio de órdenes
        order_validator: Validador de órdenes (opcional)
        
    Returns:
        PlacePendingOrderUseCase: Instancia del caso de uso
    """
    return PlacePendingOrderUseCase(order_repository, order_validator)