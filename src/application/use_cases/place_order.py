# src/application/use_cases/place_order.py
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
import logging

# Importación condicional para evitar dependencias circulares
if TYPE_CHECKING:
    from src.application.validators.order_validator import OrderValidator


@dataclass
class PlaceOrderRequest:
    """Solicitud para colocar una orden de mercado para US500."""
    
    symbol: str = "US500"  # Siempre US500
    operation: str  # 'buy' o 'sell'
    volume: float
    stop_loss: float = 0.0  # Puede ser pips positivo o nivel negativo
    take_profit: float = 0.0  # Puede ser pips positivo o nivel negativo
    comment: str = ""
    price: float = 0.0  # Precio de entrada (0 = precio actual del mercado)
    magic_number: int = 234000
    deviation: int = 10  # Desviación máxima en puntos
    sl_is_pips: bool = True  # True: SL en pips, False: SL como nivel absoluto
    tp_is_pips: bool = True  # True: TP en pips, False: TP como nivel absoluto


@dataclass
class PlaceOrderResponse:
    """Respuesta de la orden colocada."""
    
    success: bool
    message: str
    ticket: Optional[int] = None
    price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    volume: float = 0.0
    symbol: str = ""
    operation: str = ""
    timestamp: str = ""
    error_code: int = 0


class PlaceOrderUseCase:
    """Caso de uso para colocar órdenes de mercado (BUY/SELL) para US500."""
    
    def __init__(self, order_repository, order_validator: Optional["OrderValidator"] = None):
        """
        Inicializa el caso de uso para colocar órdenes.
        
        Args:
            order_repository: Repositorio MT5 para comunicación con MT5
            order_validator: Validador de órdenes (opcional)
        """
        self.order_repository = order_repository
        self.validator = order_validator
        self.logger = logging.getLogger(__name__)
        
        # Configuración específica para US500
        self.symbol = "US500"
    
    def execute(self, request: PlaceOrderRequest) -> PlaceOrderResponse:
        """
        Ejecuta la colocación de una orden de mercado para US500.
        
        Args:
            request: Datos de la orden a colocar
            
        Returns:
            PlaceOrderResponse: Resultado de la operación
        """
        try:
            self.logger.info(f"Iniciando orden {request.operation.upper()} para US500")
            
            # 1. Validar parámetros básicos (si hay validador)
            if self.validator:
                validation_result = self.validator.validate_order_request(request)
                if not validation_result["valid"]:
                    return PlaceOrderResponse(
                        success=False,
                        message=f"Validación fallida: {validation_result['message']}",
                        symbol=request.symbol,
                        operation=request.operation,
                        timestamp=datetime.now().isoformat()
                    )
            
            # 2. Convertir tipo de operación
            operation = request.operation.lower()
            if operation not in ['buy', 'sell']:
                return PlaceOrderResponse(
                    success=False,
                    message=f"Operación inválida: {request.operation}",
                    symbol=request.symbol,
                    operation=request.operation,
                    timestamp=datetime.now().isoformat()
                )
            
            # 3. Preparar niveles SL y TP para US500
            sl_level, tp_level = self._prepare_sl_tp_levels_for_us500(
                operation=operation,
                price=request.price,
                sl_value=request.stop_loss,
                tp_value=request.take_profit,
                sl_is_pips=request.sl_is_pips,
                tp_is_pips=request.tp_is_pips
            )
            
            self.logger.debug(f"SL calculado: {sl_level}, TP calculado: {tp_level}")
            
            # 4. Colocar la orden en MT5
            order_type = "BUY" if operation == 'buy' else "SELL"
            
            ticket = self.order_repository.place_order(
                symbol=self.symbol,  # Siempre US500
                order_type=order_type,
                volume=request.volume,
                price=request.price,
                stop_loss=sl_level,
                take_profit=tp_level,
                comment=request.comment
            )
            
            # 5. Verificar resultado
            if ticket:
                self.logger.info(f"✅ Orden exitosa - Ticket: {ticket}, US500 {order_type}")
                
                # Obtener precio actual para respuesta
                price_info = self.order_repository.get_current_price(self.symbol)
                executed_price = request.price if request.price > 0 else (
                    price_info['ask'] if operation == 'buy' else price_info['bid']
                )
                
                return PlaceOrderResponse(
                    success=True,
                    message=f"Orden {operation.upper()} ejecutada exitosamente",
                    ticket=ticket,
                    price=executed_price,
                    stop_loss=sl_level,
                    take_profit=tp_level,
                    volume=request.volume,
                    symbol=self.symbol,
                    operation=operation,
                    timestamp=datetime.now().isoformat()
                )
            else:
                error_msg = self.order_repository.get_last_error()
                self.logger.error(f"❌ Error al colocar orden: {error_msg}")
                
                return PlaceOrderResponse(
                    success=False,
                    message=f"Error al colocar orden: {error_msg}",
                    symbol=self.symbol,
                    operation=operation,
                    timestamp=datetime.now().isoformat(),
                    error_code=getattr(self.order_repository, 'last_error_code', 0)
                )
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada al colocar orden: {str(e)}")
            
            return PlaceOrderResponse(
                success=False,
                message=f"Error inesperado: {str(e)}",
                symbol=self.symbol,
                operation=request.operation,
                timestamp=datetime.now().isoformat()
            )
    
    def _prepare_sl_tp_levels_for_us500(self, operation: str, price: float, 
                                       sl_value: float, tp_value: float,
                                       sl_is_pips: bool = True, tp_is_pips: bool = True) -> Tuple[float, float]:
        """
        Prepara niveles de SL y TP para US500.
        
        Args:
            operation: 'buy' o 'sell'
            price: Precio de entrada
            sl_value: Valor de SL (pips positivo o nivel negativo)
            tp_value: Valor de TP (pips positivo o nivel negativo)
            sl_is_pips: True si sl_value está en pips, False si es nivel absoluto
            tp_is_pips: True si tp_value está en pips, False si es nivel absoluto
            
        Returns:
            Tuple[float, float]: (nivel_sl, nivel_tp)
        """
        # Si no hay SL/TP configurado
        if sl_value == 0 and tp_value == 0:
            return 0.0, 0.0
        
        # Obtener información de US500
        symbol_info = self.order_repository.get_symbol_info(self.symbol)
        if not symbol_info:
            return 0.0, 0.0
        
        point = symbol_info.get('point', 0.01)  # US500 usa 0.01 de punto
        current_price = price
        
        # Si no se proporcionó precio, obtener precio actual
        if current_price <= 0:
            price_info = self.order_repository.get_current_price(self.symbol)
            if price_info:
                current_price = price_info['ask'] if operation == 'buy' else price_info['bid']
            else:
                return 0.0, 0.0
        
        operation = operation.lower()
        
        # Manejar SL
        sl_level = 0.0
        if sl_value != 0:
            if sl_is_pips and sl_value > 0:
                # SL en pips positivos
                if operation == 'buy':
                    sl_level = current_price - (sl_value * point * 10)  # US500: 1 pip = 10 points
                else:  # sell
                    sl_level = current_price + (sl_value * point * 10)
            elif sl_value < 0:
                # SL como nivel absoluto (negativo)
                sl_level = abs(sl_value) * point  # Convertir a precio absoluto
        
        # Manejar TP
        tp_level = 0.0
        if tp_value != 0:
            if tp_is_pips and tp_value > 0:
                # TP en pips positivos
                if operation == 'buy':
                    tp_level = current_price + (tp_value * point * 10)
                else:  # sell
                    tp_level = current_price - (tp_value * point * 10)
            elif tp_value < 0:
                # TP como nivel absoluto (negativo)
                tp_level = abs(tp_value) * point
        
        return sl_level, tp_level


# Factory function para crear el caso de uso
def create_place_order_use_case(order_repository, order_validator=None) -> PlaceOrderUseCase:
    """
    Crea una instancia del caso de uso para colocar órdenes.
    
    Args:
        order_repository: Repositorio MT5
        order_validator: Validador de órdenes (opcional)
        
    Returns:
        PlaceOrderUseCase: Instancia del caso de uso
    """
    return PlaceOrderUseCase(order_repository, order_validator)