# src/application/use_cases/modify_position.py

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class ModifyPositionRequest:
    """Solicitud para modificar una posición existente."""
    
    ticket: int  # Ticket de la posición a modificar
    stop_loss: Optional[float] = None  # Nuevo Stop Loss (None = no modificar)
    take_profit: Optional[float] = None  # Nuevo Take Profit (None = no modificar)
    comment: str = "Modificado por aplicación"
    # Parámetros avanzados
    trailing_stop: Optional[float] = None  # Trailing stop en pips
    break_even: bool = False  # Mover SL al punto de equilibrio cuando haya profit


@dataclass
class ModifyPositionResponse:
    """Respuesta de la modificación de posición."""
    
    success: bool
    message: str
    ticket: int = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    original_sl: float = 0.0
    original_tp: float = 0.0
    price_open: float = 0.0
    symbol: str = ""
    position_type: str = ""  # 'BUY' o 'SELL'
    timestamp: str = ""


@dataclass
class ModifyAllPositionsRequest:
    """Solicitud para modificar múltiples posiciones."""
    
    filter_symbol: Optional[str] = None  # Filtrar por símbolo
    filter_type: Optional[str] = None  # 'BUY' o 'SELL'
    new_stop_loss: Optional[float] = None  # Nuevo SL para todas
    new_take_profit: Optional[float] = None  # Nuevo TP para todas
    comment: str = "Modificaciones masivas"
    # Modificaciones relativas
    add_to_sl: Optional[float] = None  # Agregar pips al SL actual
    add_to_tp: Optional[float] = None  # Agregar pips al TP actual


class ModifyPositionUseCase:
    """Caso de uso para modificar posiciones (SL/TP)."""
    
    def __init__(self, order_repository):
        """
        Inicializa el caso de uso para modificar posiciones.
        
        Args:
            order_repository: Repositorio de órdenes para comunicación con MT5
        """
        self.order_repository = order_repository
        self.validator = None  # Se importará solo cuando sea necesario
        self.logger = logging.getLogger(__name__)
    
    def execute(self, request: ModifyPositionRequest) -> ModifyPositionResponse:
        """
        Ejecuta la modificación de una posición específica.
        
        Args:
            request: Datos de modificación de la posición
            
        Returns:
            ModifyPositionResponse: Resultado de la operación
        """
        try:
            self.logger.info(f"Iniciando modificación de posición {request.ticket}")
            
            # Importar validador solo cuando sea necesario para evitar circular import
            if self.validator is None:
                from src.application.validators.order_validator import OrderValidator
                self.validator = OrderValidator()
            
            # 1. Validar que tenemos un ticket válido
            if request.ticket <= 0:
                return ModifyPositionResponse(
                    success=False,
                    message="Ticket de posición inválido",
                    ticket=request.ticket,
                    timestamp=datetime.now().isoformat()
                )
            
            # 2. Obtener información de la posición actual
            position = self.order_repository.get_position_by_ticket(request.ticket)
            if not position:
                return ModifyPositionResponse(
                    success=False,
                    message=f"No se encontró la posición con ticket {request.ticket}",
                    ticket=request.ticket,
                    timestamp=datetime.now().isoformat()
                )
            
            # 3. Extraer datos de la posición
            symbol = position.get('symbol', '')
            position_type = position.get('type', '')
            price_open = position.get('open_price', 0.0)
            current_sl = position.get('sl', 0.0)
            current_tp = position.get('tp', 0.0)
            
            # 4. Preparar nuevos niveles SL/TP
            new_sl, new_tp, validation_message = self._prepare_new_levels(
                symbol=symbol,
                position_type=position_type,
                price_open=price_open,
                current_sl=current_sl,
                current_tp=current_tp,
                new_sl=request.stop_loss,
                new_tp=request.take_profit,
                trailing_stop=request.trailing_stop,
                break_even=request.break_even
            )
            
            if validation_message:
                return ModifyPositionResponse(
                    success=False,
                    message=validation_message,
                    ticket=request.ticket,
                    symbol=symbol,
                    position_type=position_type,
                    price_open=price_open,
                    original_sl=current_sl,
                    original_tp=current_tp,
                    timestamp=datetime.now().isoformat()
                )
            
            # 5. Si no hay cambios, retornar éxito sin modificar
            if new_sl == current_sl and new_tp == current_tp:
                return ModifyPositionResponse(
                    success=True,
                    message="No se requieren cambios (valores idénticos)",
                    ticket=request.ticket,
                    stop_loss=current_sl,
                    take_profit=current_tp,
                    original_sl=current_sl,
                    original_tp=current_tp,
                    price_open=price_open,
                    symbol=symbol,
                    position_type=position_type,
                    timestamp=datetime.now().isoformat()
                )
            
            # 6. Aplicar la modificación
            success = self.order_repository.modify_position(
                ticket=request.ticket,
                stop_loss=new_sl if new_sl != current_sl else None,
                take_profit=new_tp if new_tp != current_tp else None
            )
            
            # 7. Procesar resultado
            if success:
                self.logger.info(f"✅ Modificación exitosa - Ticket: {request.ticket}")
                
                # Registrar cambios
                changes = []
                if new_sl != current_sl:
                    changes.append(f"SL: {current_sl:.5f} → {new_sl:.5f}")
                if new_tp != current_tp:
                    changes.append(f"TP: {current_tp:.5f} → {new_tp:.5f}")
                
                return ModifyPositionResponse(
                    success=True,
                    message=f"Posición modificada: {', '.join(changes)}",
                    ticket=request.ticket,
                    stop_loss=new_sl,
                    take_profit=new_tp,
                    original_sl=current_sl,
                    original_tp=current_tp,
                    price_open=price_open,
                    symbol=symbol,
                    position_type=position_type,
                    timestamp=datetime.now().isoformat()
                )
            else:
                error_msg = self.order_repository.get_last_error()
                self.logger.error(f"❌ Error al modificar posición: {error_msg}")
                
                return ModifyPositionResponse(
                    success=False,
                    message=f"Error al modificar: {error_msg}",
                    ticket=request.ticket,
                    original_sl=current_sl,
                    original_tp=current_tp,
                    price_open=price_open,
                    symbol=symbol,
                    position_type=position_type,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada al modificar posición: {str(e)}")
            
            return ModifyPositionResponse(
                success=False,
                message=f"Error inesperado: {str(e)}",
                ticket=request.ticket,
                timestamp=datetime.now().isoformat()
            )
    
    def execute_modify_all(self, request: ModifyAllPositionsRequest) -> Dict[str, Any]:
        """
        Modifica múltiples posiciones según criterios.
        
        Args:
            request: Configuración para modificaciones masivas
            
        Returns:
            Dict[str, Any]: Resultado de las operaciones
        """
        try:
            self.logger.info("Iniciando modificaciones masivas de posiciones...")
            
            # Importar validador solo cuando sea necesario para evitar circular import
            if self.validator is None:
                from src.application.validators.order_validator import OrderValidator
                self.validator = OrderValidator()
            
            # Obtener todas las posiciones
            positions = self.order_repository.get_open_positions()
            
            if not positions:
                return {
                    "success": True,
                    "message": "No hay posiciones abiertas para modificar",
                    "total_positions": 0,
                    "modified": 0,
                    "failed": 0,
                    "details": []
                }
            
            # Aplicar filtros
            filtered_positions = positions
            
            if request.filter_symbol:
                filtered_positions = [p for p in filtered_positions 
                                    if p.get('symbol') == request.filter_symbol]
            
            if request.filter_type:
                filtered_positions = [p for p in filtered_positions 
                                    if p.get('type') == request.filter_type]
            
            if not filtered_positions:
                return {
                    "success": True,
                    "message": "No hay posiciones que coincidan con los filtros",
                    "total_positions": 0,
                    "modified": 0,
                    "failed": 0,
                    "details": []
                }
            
            self.logger.info(f"Aplicando modificaciones a {len(filtered_positions)} posiciones...")
            
            modified_count = 0
            failed_count = 0
            details = []
            
            for position in filtered_positions:
                ticket = position.get('ticket')
                symbol = position.get('symbol')
                position_type = position.get('type')
                current_sl = position.get('sl', 0.0)
                current_tp = position.get('tp', 0.0)
                price_open = position.get('open_price', 0.0)
                
                # Calcular nuevos niveles
                new_sl = request.new_stop_loss
                new_tp = request.new_take_profit
                
                # Aplicar modificaciones relativas si se especifican
                if request.add_to_sl is not None and current_sl > 0:
                    new_sl = self._calculate_relative_level(
                        symbol, position_type, price_open, current_sl, request.add_to_sl
                    )
                
                if request.add_to_tp is not None and current_tp > 0:
                    new_tp = self._calculate_relative_level(
                        symbol, position_type, price_open, current_tp, request.add_to_tp
                    )
                
                # Saltar si no hay cambios
                if new_sl == current_sl and new_tp == current_tp:
                    details.append({
                        "ticket": ticket,
                        "symbol": symbol,
                        "status": "skipped",
                        "reason": "No changes required"
                    })
                    continue
                
                # Aplicar modificación
                success = self.order_repository.modify_position(
                    ticket=ticket,
                    stop_loss=new_sl if new_sl != current_sl else None,
                    take_profit=new_tp if new_tp != current_tp else None
                )
                
                if success:
                    modified_count += 1
                    details.append({
                        "ticket": ticket,
                        "symbol": symbol,
                        "type": position_type,
                        "status": "modified",
                        "changes": {
                            "sl": {"from": current_sl, "to": new_sl},
                            "tp": {"from": current_tp, "to": new_tp}
                        }
                    })
                    self.logger.debug(f"✅ Modificada posición {ticket}")
                else:
                    failed_count += 1
                    error_msg = self.order_repository.get_last_error()
                    details.append({
                        "ticket": ticket,
                        "symbol": symbol,
                        "type": position_type,
                        "status": "failed",
                        "error": error_msg
                    })
                    self.logger.error(f"❌ Error modificando posición {ticket}: {error_msg}")
            
            # Preparar respuesta
            total_modified = modified_count + failed_count
            success_rate = (modified_count / total_modified * 100) if total_modified > 0 else 100
            
            return {
                "success": modified_count > 0,
                "message": f"Modificadas {modified_count}/{len(filtered_positions)} posiciones ({success_rate:.1f}% éxito)",
                "total_positions": len(filtered_positions),
                "modified": modified_count,
                "failed": failed_count,
                "success_rate": success_rate,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada en modificaciones masivas: {str(e)}")
            
            return {
                "success": False,
                "message": f"Error inesperado: {str(e)}",
                "total_positions": 0,
                "modified": 0,
                "failed": 0,
                "details": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def _prepare_new_levels(self, symbol: str, position_type: str, price_open: float,
                           current_sl: float, current_tp: float, new_sl: Optional[float],
                           new_tp: Optional[float], trailing_stop: Optional[float],
                           break_even: bool) -> Tuple[float, float, str]:
        """
        Prepara y valida los nuevos niveles SL/TP.
        
        Returns:
            Tuple[float, float, str]: (nuevo_sl, nuevo_tp, mensaje_error)
        """
        # Usar valores actuales como base
        final_sl = current_sl
        final_tp = current_tp
        
        # Manejar trailing stop
        if trailing_stop is not None and trailing_stop > 0:
            # En una implementación real, calcularíamos el trailing stop basado en el precio actual
            # Por ahora, solo lo registramos
            self.logger.info(f"Trailing stop de {trailing_stop} pips solicitado para {symbol}")
            # Nota: El trailing stop normalmente se maneja de manera diferente
        
        # Manejar break even
        if break_even:
            # Mover SL al punto de equilibrio (precio de apertura)
            final_sl = price_open
            self.logger.info(f"Break even activado - SL movido a {price_open}")
        
        # Aplicar nuevos valores SL/TP si se especifican
        if new_sl is not None:
            final_sl = new_sl
        
        if new_tp is not None:
            final_tp = new_tp
        
        # Validar niveles
        validation_result = self._validate_levels(
            symbol=symbol,
            position_type=position_type,
            price_open=price_open,
            stop_loss=final_sl,
            take_profit=final_tp
        )
        
        if not validation_result["valid"]:
            return current_sl, current_tp, validation_result["message"]
        
        return final_sl, final_tp, ""
    
    def _validate_levels(self, symbol: str, position_type: str, 
                        price_open: float, stop_loss: float, take_profit: float) -> Dict[str, Any]:
        """
        Valida que los niveles SL/TP sean apropiados.
        
        Args:
            symbol: Símbolo del activo
            position_type: 'BUY' o 'SELL'
            price_open: Precio de apertura
            stop_loss: Nivel de Stop Loss propuesto
            take_profit: Nivel de Take Profit propuesto
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        # Importar validador solo cuando sea necesario para evitar circular import
        if self.validator is None:
            from src.application.validators.order_validator import OrderValidator
            self.validator = OrderValidator()
        
        # Obtener información del símbolo
        symbol_info = self._get_symbol_info(symbol)
        point = symbol_info.get('point', 0.00001)
        
        # Validar SL si es mayor que 0
        if stop_loss > 0:
            # Calcular distancia mínima
            min_sl_distance_pips = 10  # Mínimo 10 pips
            
            if position_type == 'BUY':
                # Para compras: SL debe estar POR DEBAJO del precio de apertura
                if stop_loss >= price_open:
                    return {
                        "valid": False,
                        "message": "Para posiciones de COMPRA, el SL debe estar por debajo del precio de apertura"
                    }
                
                # Validar distancia mínima
                sl_distance_pips = (price_open - stop_loss) / point
                if sl_distance_pips < min_sl_distance_pips:
                    return {
                        "valid": False,
                        "message": f"SL debe estar al menos a {min_sl_distance_pips} pips del precio de apertura"
                    }
            
            else:  # SELL
                # Para ventas: SL debe estar POR ENCIMA del precio de apertura
                if stop_loss <= price_open:
                    return {
                        "valid": False,
                        "message": "Para posiciones de VENTA, el SL debe estar por encima del precio de apertura"
                    }
                
                # Validar distancia mínima
                sl_distance_pips = (stop_loss - price_open) / point
                if sl_distance_pips < min_sl_distance_pips:
                    return {
                        "valid": False,
                        "message": f"SL debe estar al menos a {min_sl_distance_pips} pips del precio de apertura"
                    }
        
        # Validar TP si es mayor que 0
        if take_profit > 0:
            # Calcular distancia mínima
            min_tp_distance_pips = 10  # Mínimo 10 pips
            
            if position_type == 'BUY':
                # Para compras: TP debe estar POR ENCIMA del precio de apertura
                if take_profit <= price_open:
                    return {
                        "valid": False,
                        "message": "Para posiciones de COMPRA, el TP debe estar por encima del precio de apertura"
                    }
                
                # Validar distancia mínima
                tp_distance_pips = (take_profit - price_open) / point
                if tp_distance_pips < min_tp_distance_pips:
                    return {
                        "valid": False,
                        "message": f"TP debe estar al menos a {min_tp_distance_pips} pips del precio de apertura"
                    }
            
            else:  # SELL
                # Para ventas: TP debe estar POR DEBAJO del precio de apertura
                if take_profit >= price_open:
                    return {
                        "valid": False,
                        "message": "Para posiciones de VENTA, el TP debe estar por debajo del precio de apertura"
                    }
                
                # Validar distancia mínima
                tp_distance_pips = (price_open - take_profit) / point
                if tp_distance_pips < min_tp_distance_pips:
                    return {
                        "valid": False,
                        "message": f"TP debe estar al menos a {min_tp_distance_pips} pips del precio de apertura"
                    }
        
        # Validar ratio SL/TP si ambos están configurados
        if stop_loss > 0 and take_profit > 0 and price_open > 0:
            if position_type == 'BUY':
                risk = price_open - stop_loss
                reward = take_profit - price_open
            else:  # SELL
                risk = stop_loss - price_open
                reward = price_open - take_profit
            
            if risk > 0 and reward > 0:
                risk_reward_ratio = reward / risk
                if risk_reward_ratio < 0.5:  # Mínimo ratio 1:0.5
                    return {
                        "valid": False,
                        "message": f"Ratio riesgo/recompensa muy bajo ({risk_reward_ratio:.2f}). Mínimo recomendado: 0.5"
                    }
        
        return {"valid": True, "message": "Niveles válidos"}
    
    def _calculate_relative_level(self, symbol: str, position_type: str, 
                                 price_open: float, current_level: float, 
                                 add_pips: float) -> float:
        """
        Calcula un nuevo nivel relativo agregando pips.
        
        Args:
            symbol: Símbolo del activo
            position_type: 'BUY' o 'SELL'
            price_open: Precio de apertura
            current_level: Nivel actual (SL o TP)
            add_pips: Pips a agregar (puede ser negativo para restar)
            
        Returns:
            float: Nuevo nivel calculado
        """
        if current_level <= 0 or add_pips == 0:
            return current_level
        
        symbol_info = self._get_symbol_info(symbol)
        point = symbol_info.get('point', 0.00001)
        
        # Calcular cambio en precio
        price_change = add_pips * point
        
        # Aplicar cambio
        new_level = current_level + price_change
        
        # Validar dirección básica
        if position_type == 'BUY':
            # Para SL: debe seguir estando por debajo del precio de apertura
            if new_level > 0 and new_level >= price_open:
                new_level = price_open - (10 * point)  # Mantener distancia mínima
        else:  # SELL
            # Para SL: debe seguir estando por encima del precio de apertura
            if new_level > 0 and new_level <= price_open:
                new_level = price_open + (10 * point)  # Mantener distancia mínima
        
        return new_level
    
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
            'EURUSD': {'point': 0.00001, 'digits': 5},
            'US500': {'point': 0.01, 'digits': 2},
            'GBPUSD': {'point': 0.00001, 'digits': 5},
            'USDJPY': {'point': 0.001, 'digits': 3},
            'XAUUSD': {'point': 0.01, 'digits': 2}
        }
        
        return default_info.get(symbol, {'point': 0.00001, 'digits': 5})


# Factory function para crear el caso de uso
def create_modify_position_use_case(order_repository) -> ModifyPositionUseCase:
    """
    Crea una instancia del caso de uso para modificar posiciones.
    
    Args:
        order_repository: Repositorio de órdenes
        
    Returns:
        ModifyPositionUseCase: Instancia del caso de uso
    """
    return ModifyPositionUseCase(order_repository)