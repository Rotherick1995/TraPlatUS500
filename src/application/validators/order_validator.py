# src/application/validators/order_validator.py

from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime


class OrderValidator:
    """Validador para parámetros de órdenes y posiciones."""
    
    def __init__(self):
        """Inicializa el validador."""
        self.logger = logging.getLogger(__name__)
        self.min_volume = 0.01  # Volumen mínimo global
        self.max_volume = 100.0
        self.min_pips = 1
        self.max_pips = 10000
        self.min_price = 0.00001
        self.max_price = 1000000.0
        
        # Configuración de símbolos CORREGIDA con valores REALES de MT5
        self.symbol_config = {
            'EURUSD': {
                'point': 0.00001,
                'digits': 5,
                'min_volume': 0.01,      # Mínimo 0.01 lote
                'max_volume': 100.0,
                'volume_step': 0.01,     # Step de 0.01
                'min_distance_pips': 2,
                'spread': 10
            },
            'US500': {
                'point': 0.1,           # CORREGIDO: 0.1 (no 0.01)
                'digits': 1,            # CORREGIDO: 1 dígito (no 2)
                'min_volume': 0.1,      # ¡CORREGIDO! Mínimo 0.1 lote (no 0.01)
                'max_volume': 500.0,    # Ajustado a 500 según MT5
                'volume_step': 0.1,     # Step de 0.1 (múltiplos de 0.1)
                'min_distance_pips': 2,
                'spread': 25
            },
            'GBPUSD': {
                'point': 0.00001,
                'digits': 5,
                'min_volume': 0.01,
                'max_volume': 100.0,
                'volume_step': 0.01,
                'min_distance_pips': 2,
                'spread': 12
            },
            'USDJPY': {
                'point': 0.001,
                'digits': 3,
                'min_volume': 0.01,
                'max_volume': 100.0,
                'volume_step': 0.01,
                'min_distance_pips': 2,
                'spread': 8
            },
            'XAUUSD': {
                'point': 0.01,
                'digits': 2,
                'min_volume': 0.01,
                'max_volume': 50.0,
                'volume_step': 0.01,
                'min_distance_pips': 5,
                'spread': 30
            },
            # Símbolos adicionales
            'AUDUSD': {
                'point': 0.00001,
                'digits': 5,
                'min_volume': 0.01,
                'max_volume': 100.0,
                'volume_step': 0.01,
                'min_distance_pips': 2,
                'spread': 10
            },
            'USDCHF': {
                'point': 0.00001,
                'digits': 5,
                'min_volume': 0.01,
                'max_volume': 100.0,
                'volume_step': 0.01,
                'min_distance_pips': 2,
                'spread': 10
            },
            'US30': {
                'point': 0.1,           # Índices usan 0.1
                'digits': 1,
                'min_volume': 0.1,      # Mínimo 0.1 lote
                'max_volume': 500.0,
                'volume_step': 0.1,     # Step de 0.1
                'min_distance_pips': 2,
                'spread': 20
            },
            'NAS100': {
                'point': 0.1,           # Índices usan 0.1
                'digits': 1,
                'min_volume': 0.1,      # Mínimo 0.1 lote
                'max_volume': 500.0,
                'volume_step': 0.1,     # Step de 0.1
                'min_distance_pips': 2,
                'spread': 15
            },
            'BTCUSD': {
                'point': 0.01,
                'digits': 2,
                'min_volume': 0.01,
                'max_volume': 10.0,
                'volume_step': 0.01,
                'min_distance_pips': 10,
                'spread': 50
            },
            'ETHUSD': {
                'point': 0.01,
                'digits': 2,
                'min_volume': 0.01,
                'max_volume': 10.0,
                'volume_step': 0.01,
                'min_distance_pips': 10,
                'spread': 40
            }
        }
    
    def validate_order_request(self, request) -> Dict[str, Any]:
        """
        Valida una solicitud de orden de mercado.
        
        Args:
            request: Solicitud de orden de mercado (PlaceOrderRequest)
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        try:
            self.logger.debug(f"Validando orden para {request.symbol}")
            
            errors = []
            
            # 1. Validar símbolo
            if not request.symbol or len(request.symbol) < 3:
                errors.append("Símbolo inválido o vacío")
            
            # 2. Validar operación
            valid_operations = ['buy', 'sell', 'compra', 'venta', 'long', 'short']
            if request.operation.lower() not in valid_operations:
                errors.append(f"Operación inválida. Válidas: {', '.join(valid_operations)}")
            
            # 3. Validar volumen (con ajuste automático para índices)
            volume_error = self._validate_volume(request.symbol, request.volume)
            if volume_error:
                errors.append(volume_error)
            
            # 4. Validar SL y TP (si están configurados)
            if request.stop_loss != 0:
                sl_error = self._validate_stop_loss(
                    symbol=request.symbol,
                    operation=request.operation,
                    price=request.price,
                    stop_loss=request.stop_loss,
                    is_pips=request.sl_is_pips
                )
                if sl_error:
                    errors.append(sl_error)
            
            if request.take_profit != 0:
                tp_error = self._validate_take_profit(
                    symbol=request.symbol,
                    operation=request.operation,
                    price=request.price,
                    take_profit=request.take_profit,
                    is_pips=request.tp_is_pips
                )
                if tp_error:
                    errors.append(tp_error)
            
            # 5. Validar ratio riesgo/recompensa (SOLO si ambos están configurados)
            if request.stop_loss != 0 and request.take_profit != 0:
                rr_error = self._validate_risk_reward_ratio(
                    symbol=request.symbol,
                    operation=request.operation,
                    price=request.price,
                    stop_loss=request.stop_loss,
                    take_profit=request.take_profit,
                    sl_is_pips=request.sl_is_pips,
                    tp_is_pips=request.tp_is_pips
                )
                if rr_error:
                    # Solo advertir, no bloquear la orden
                    self.logger.warning(rr_error)
            
            # 6. Validar precio (si se especifica)
            if request.price != 0:
                price_error = self._validate_price(request.symbol, request.price)
                if price_error:
                    errors.append(price_error)
            
            # 7. Validar formato de volumen según símbolo
            volume_step_error = self._validate_volume_step(request.symbol, request.volume)
            if volume_step_error:
                errors.append(volume_step_error)
            
            if errors:
                return {
                    "valid": False,
                    "message": " | ".join(errors),
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "valid": True,
                "message": "Validación exitosa",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error en validación de orden: {str(e)}")
            return {
                "valid": False,
                "message": f"Error de validación: {str(e)}",
                "errors": [str(e)],
                "timestamp": datetime.now().isoformat()
            }
    
    def validate_pending_order_request(self, request) -> Dict[str, Any]:
        """
        Valida una solicitud de orden pendiente.
        
        Args:
            request: Solicitud de orden pendiente (PlacePendingOrderRequest)
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        try:
            self.logger.debug(f"Validando orden pendiente para {request.symbol}")
            
            errors = []
            
            # 1. Validar símbolo
            if not request.symbol or len(request.symbol) < 3:
                errors.append("Símbolo inválido o vacío")
            
            # 2. Validar tipo de orden
            valid_order_types = ['LIMIT_BUY', 'LIMIT_SELL', 'STOP_BUY', 'STOP_SELL']
            if request.order_type not in valid_order_types:
                errors.append(f"Tipo de orden inválido. Válidos: {', '.join(valid_order_types)}")
            
            # 3. Validar volumen
            volume_error = self._validate_volume(request.symbol, request.volume)
            if volume_error:
                errors.append(volume_error)
            
            # 4. Validar precio de activación
            if request.price <= 0:
                errors.append("El precio de activación debe ser mayor que cero")
            else:
                price_error = self._validate_price(request.symbol, request.price)
                if price_error:
                    errors.append(price_error)
            
            # 5. Validar SL y TP (si están configurados)
            if request.stop_loss != 0:
                sl_error = self._validate_pending_sl_tp(
                    symbol=request.symbol,
                    order_type=request.order_type,
                    activation_price=request.price,
                    level=request.stop_loss,
                    is_stop_loss=True
                )
                if sl_error:
                    errors.append(sl_error)
            
            if request.take_profit != 0:
                tp_error = self._validate_pending_sl_tp(
                    symbol=request.symbol,
                    order_type=request.order_type,
                    activation_price=request.price,
                    level=request.take_profit,
                    is_stop_loss=False
                )
                if tp_error:
                    errors.append(tp_error)
            
            # 6. Validar expiración (si se especifica)
            if request.expiration and request.expiration < datetime.now():
                errors.append("La fecha de expiración no puede ser en el pasado")
            
            # 7. Validar formato de volumen según símbolo
            volume_step_error = self._validate_volume_step(request.symbol, request.volume)
            if volume_step_error:
                errors.append(volume_step_error)
            
            if errors:
                return {
                    "valid": False,
                    "message": " | ".join(errors),
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "valid": True,
                "message": "Validación exitosa",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error en validación de orden pendiente: {str(e)}")
            return {
                "valid": False,
                "message": f"Error de validación: {str(e)}",
                "errors": [str(e)],
                "timestamp": datetime.now().isoformat()
            }
    
    def validate_modify_request(self, request) -> Dict[str, Any]:
        """
        Valida una solicitud de modificación de posición.
        
        Args:
            request: Solicitud de modificación (ModifyPositionRequest)
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        try:
            self.logger.debug(f"Validando modificación para posición {request.ticket}")
            
            errors = []
            
            # 1. Validar ticket
            if request.ticket <= 0:
                errors.append("Ticket de posición inválido")
            
            # 2. Validar que al menos un parámetro sea modificado
            if (request.stop_loss is None and request.take_profit is None and 
                request.trailing_stop is None and not request.break_even):
                errors.append("Debe especificar al menos un parámetro a modificar (SL, TP, trailing stop o break even)")
            
            # 3. Validar trailing stop
            if request.trailing_stop is not None:
                if request.trailing_stop < 0:
                    errors.append("El trailing stop no puede ser negativo")
                elif request.trailing_stop > 0 and request.trailing_stop < 10:
                    errors.append("El trailing stop debe ser de al menos 10 pips")
            
            if errors:
                return {
                    "valid": False,
                    "message": " | ".join(errors),
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "valid": True,
                "message": "Validación exitosa",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error en validación de modificación: {str(e)}")
            return {
                "valid": False,
                "message": f"Error de validación: {str(e)}",
                "errors": [str(e)],
                "timestamp": datetime.now().isoformat()
            }
    
    def _validate_volume(self, symbol: str, volume: float) -> Optional[str]:
        """
        Valida el volumen de la operación.
        
        Args:
            symbol: Símbolo del activo
            volume: Volumen en lotes
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if volume <= 0:
            return "El volumen debe ser mayor que cero"
        
        # Obtener configuración del símbolo
        config = self._get_symbol_config(symbol)
        min_volume = config.get('min_volume', self.min_volume)
        max_volume = config.get('max_volume', self.max_volume)
        
        if volume < min_volume:
            return f"Volumen mínimo para {symbol} es {min_volume} lote(s)"
        
        if volume > max_volume:
            return f"Volumen máximo para {symbol} es {max_volume} lote(s)"
        
        return None
    
    def _validate_volume_step(self, symbol: str, volume: float) -> Optional[str]:
        """
        Valida que el volumen sea múltiplo del step permitido.
        
        Args:
            symbol: Símbolo del activo
            volume: Volumen en lotes
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        config = self._get_symbol_config(symbol)
        volume_step = config.get('volume_step', 0.01)
        
        # Verificar que sea múltiplo del step
        try:
            # Redondear para evitar problemas de punto flotante
            normalized_volume = round(volume / volume_step, 10)
            if not abs(normalized_volume - round(normalized_volume)) < 0.0001:
                return f"Para {symbol}, el volumen debe ser múltiplo de {volume_step} (ej: {volume_step}, {volume_step*2}, {volume_step*3})"
        except:
            return f"Volumen inválido para {symbol}"
        
        return None
    
    def _validate_price(self, symbol: str, price: float) -> Optional[str]:
        """
        Valida un precio.
        
        Args:
            symbol: Símbolo del activo
            price: Precio a validar
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if price <= 0:
            return "El precio debe ser mayor que cero"
        
        if price < self.min_price:
            return f"El precio es demasiado bajo. Mínimo: {self.min_price}"
        
        if price > self.max_price:
            return f"El precio es demasiado alto. Máximo: {self.max_price}"
        
        # Validar dígitos según símbolo
        config = self._get_symbol_config(symbol)
        digits = config.get('digits', 5)
        
        # Verificar que el precio tenga el número correcto de decimales
        price_str = str(price)
        if '.' in price_str:
            decimal_part = price_str.split('.')[1]
            if len(decimal_part) > digits:
                return f"Precio tiene demasiados decimales para {symbol}. Máximo: {digits}"
        
        return None
    
    def _validate_stop_loss(self, symbol: str, operation: str, price: float, 
                           stop_loss: float, is_pips: bool = True) -> Optional[str]:
        """
        Valida un Stop Loss.
        
        Args:
            symbol: Símbolo del activo
            operation: Tipo de operación ('buy' o 'sell')
            price: Precio de referencia
            stop_loss: Valor de SL (pips o nivel)
            is_pips: True si stop_loss está en pips
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if stop_loss == 0:
            return None
        
        operation = operation.lower()
        config = self._get_symbol_config(symbol)
        point = config.get('point', 0.00001)
        
        # Calcular nivel absoluto
        if is_pips:
            if stop_loss < 0:
                return "Los pips de SL no pueden ser negativos"
            
            if stop_loss > self.max_pips:
                return f"SL demasiado grande. Máximo: {self.max_pips} pips"
            
            # Solo advertir para SL muy pequeño, no bloquear
            if stop_loss < self.min_pips:
                self.logger.warning(f"SL de {stop_loss} pips es muy pequeño para {symbol}")
            
            # Convertir a nivel absoluto para validación
            if operation == 'buy':
                sl_level = price - (stop_loss * point)
            else:  # sell
                sl_level = price + (stop_loss * point)
        else:
            # SL como nivel absoluto (negativo en la UI)
            sl_level = abs(stop_loss) if stop_loss < 0 else 0.0
            
            if sl_level == 0:
                return None
        
        # Validar dirección según operación
        if operation == 'buy':
            if sl_level >= price:
                return "Para operaciones de COMPRA, el SL debe estar por debajo del precio"
        else:  # sell
            if sl_level <= price:
                return "Para operaciones de VENTA, el SL debe estar por encima del precio"
        
        # Solo advertir, no bloquear por distancia mínima
        min_distance_pips = config.get('min_distance_pips', 2)
        if is_pips and stop_loss < min_distance_pips:
            self.logger.warning(f"SL de {stop_loss} pips está muy cerca del precio para {symbol}")
        
        # Validar que el nivel sea válido
        price_error = self._validate_price(symbol, sl_level)
        if price_error:
            return f"SL inválido: {price_error}"
        
        return None
    
    def _validate_take_profit(self, symbol: str, operation: str, price: float, 
                             take_profit: float, is_pips: bool = True) -> Optional[str]:
        """
        Valida un Take Profit.
        
        Args:
            symbol: Símbolo del activo
            operation: Tipo de operación ('buy' o 'sell')
            price: Precio de referencia
            take_profit: Valor de TP (pips o nivel)
            is_pips: True si take_profit está en pips
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if take_profit == 0:
            return None
        
        operation = operation.lower()
        config = self._get_symbol_config(symbol)
        point = config.get('point', 0.00001)
        
        # Calcular nivel absoluto
        if is_pips:
            if take_profit < 0:
                return "Los pips de TP no pueden ser negativos"
            
            if take_profit > self.max_pips:
                return f"TP demasiado grande. Máximo: {self.max_pips} pips"
            
            # Solo advertir para TP muy pequeño, no bloquear
            if take_profit < self.min_pips:
                self.logger.warning(f"TP de {take_profit} pips es muy pequeño para {symbol}")
            
            # Convertir a nivel absoluto para validación
            if operation == 'buy':
                tp_level = price + (take_profit * point)
            else:  # sell
                tp_level = price - (take_profit * point)
        else:
            # TP como nivel absoluto (negativo en la UI)
            tp_level = abs(take_profit) if take_profit < 0 else 0.0
            
            if tp_level == 0:
                return None
        
        # Validar dirección según operación
        if operation == 'buy':
            if tp_level <= price:
                return "Para operaciones de COMPRA, el TP debe estar por encima del precio"
        else:  # sell
            if tp_level >= price:
                return "Para operaciones de VENTA, el TP debe estar por debajo del precio"
        
        # Solo advertir, no bloquear por distancia mínima
        min_distance_pips = config.get('min_distance_pips', 2)
        if is_pips and take_profit < min_distance_pips:
            self.logger.warning(f"TP de {take_profit} pips está muy cerca del precio para {symbol}")
        
        # Validar que el nivel sea válido
        price_error = self._validate_price(symbol, tp_level)
        if price_error:
            return f"TP inválido: {price_error}"
        
        return None
    
    def _validate_pending_sl_tp(self, symbol: str, order_type: str, activation_price: float,
                               level: float, is_stop_loss: bool = True) -> Optional[str]:
        """
        Valida SL/TP para órdenes pendientes.
        
        Args:
            symbol: Símbolo del activo
            order_type: Tipo de orden pendiente
            activation_price: Precio de activación
            level: Nivel de SL o TP
            is_stop_loss: True si es SL, False si es TP
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if level == 0:
            return None
        
        # Validar que el nivel sea válido
        price_error = self._validate_price(symbol, level)
        if price_error:
            type_str = "SL" if is_stop_loss else "TP"
            return f"{type_str} inválido: {price_error}"
        
        # Determinar dirección según tipo de orden
        order_type_lower = order_type.lower()
        is_buy = 'buy' in order_type_lower
        
        # Validar dirección
        if is_stop_loss:
            # Validar SL
            if is_buy:
                # Para órdenes de compra: SL debe estar por debajo
                if level >= activation_price:
                    return "Para órdenes de compra, el SL debe estar por debajo del precio de activación"
            else:
                # Para órdenes de venta: SL debe estar por encima
                if level <= activation_price:
                    return "Para órdenes de venta, el SL debe estar por encima del precio de activación"
        else:
            # Validar TP
            if is_buy:
                # Para órdenes de compra: TP debe estar por encima
                if level <= activation_price:
                    return "Para órdenes de compra, el TP debe estar por encima del precio de activación"
            else:
                # Para órdenes de venta: TP debe estar por debajo
                if level >= activation_price:
                    return "Para órdenes de venta, el TP debe estar por debajo del precio de activación"
        
        return None
    
    def _validate_risk_reward_ratio(self, symbol: str, operation: str, price: float,
                                   stop_loss: float, take_profit: float,
                                   sl_is_pips: bool = True, tp_is_pips: bool = True) -> Optional[str]:
        """
        Valida el ratio riesgo/recompensa.
        
        Args:
            symbol: Símbolo del activo
            operation: Tipo de operación
            price: Precio de referencia
            stop_loss: Valor de SL
            take_profit: Valor de TP
            sl_is_pips: True si SL está en pips
            tp_is_pips: True si TP está en pips
            
        Returns:
            Optional[str]: Mensaje de error o None si es válido
        """
        if stop_loss == 0 or take_profit == 0 or price <= 0:
            return None
        
        operation = operation.lower()
        config = self._get_symbol_config(symbol)
        point = config.get('point', 0.00001)
        
        # Calcular niveles absolutos
        if sl_is_pips:
            if operation == 'buy':
                sl_level = price - (stop_loss * point)
            else:  # sell
                sl_level = price + (stop_loss * point)
        else:
            sl_level = abs(stop_loss) if stop_loss < 0 else 0.0
        
        if tp_is_pips:
            if operation == 'buy':
                tp_level = price + (take_profit * point)
            else:  # sell
                tp_level = price - (take_profit * point)
        else:
            tp_level = abs(take_profit) if take_profit < 0 else 0.0
        
        # Calcular riesgo y recompensa
        if operation == 'buy':
            risk = price - sl_level
            reward = tp_level - price
        else:  # sell
            risk = sl_level - price
            reward = price - tp_level
        
        # Validar que ambos sean positivos
        if risk <= 0 or reward <= 0:
            return "No se puede calcular ratio riesgo/recompensa con valores inválidos"
        
        # Calcular ratio
        ratio = reward / risk
        
        # Solo advertir, no bloquear por ratio
        min_ratio = 0.5  # Mínimo 1:0.5
        if ratio < min_ratio:
            return f"Ratio riesgo/recompensa muy bajo ({ratio:.2f}). Mínimo recomendado: {min_ratio}"
        
        max_ratio = 50.0  # Muy flexible para permitir cualquier ratio
        if ratio > max_ratio:
            return f"Ratio riesgo/recompensa muy alto ({ratio:.2f})"
        
        return None
    
    def _get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene la configuración para un símbolo.
        
        Args:
            symbol: Símbolo a consultar
            
        Returns:
            Dict[str, Any]: Configuración del símbolo
        """
        return self.symbol_config.get(symbol, {
            'point': 0.00001,
            'digits': 5,
            'min_volume': self.min_volume,
            'max_volume': self.max_volume,
            'volume_step': 0.01,
            'min_distance_pips': 2,
            'spread': 10
        })
    
    def validate_market_hours(self, symbol: str) -> Dict[str, Any]:
        """
        Valida si el mercado está abierto para un símbolo.
        
        Args:
            symbol: Símbolo a validar
            
        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        now = datetime.now()
        weekday = now.weekday()  # 0 = lunes, 6 = domingo
        
        # Mercados Forex generalmente abren domingo 22:00 hasta viernes 22:00 GMT
        market_open = weekday < 5  # Lunes a viernes
        
        if not market_open:
            return {
                "open": False,
                "message": "Mercado cerrado (fin de semana)",
                "timestamp": now.isoformat()
            }
        
        return {
            "open": True,
            "message": "Mercado abierto",
            "timestamp": now.isoformat()
        }
    
    def validate_margin(self, symbol: str, volume: float, price: float = 0) -> Dict[str, Any]:
        """
        Valida el margen requerido para una operación.
        
        Args:
            symbol: Símbolo del activo
            volume: Volumen en lotes
            price: Precio (opcional, usar precio actual si no se especifica)
            
        Returns:
            Dict[str, Any]: Información de margen
        """
        try:
            # Primero validar el volumen
            volume_error = self._validate_volume(symbol, volume)
            if volume_error:
                return {
                    "margin_required": 0,
                    "is_valid": False,
                    "message": f"Volumen inválido: {volume_error}",
                    "timestamp": datetime.now().isoformat()
                }
            
            config = self._get_symbol_config(symbol)
            
            # Valores aproximados para cálculo
            contract_size = 100000  # Tamaño estándar de contrato Forex
            leverage = 100  # Apalancamiento 1:100
            
            # Calcular margen aproximado
            if price <= 0:
                # Usar precio aproximado según símbolo
                price_approx = {
                    'EURUSD': 1.10000,
                    'US500': 5000.00,
                    'GBPUSD': 1.25000,
                    'USDJPY': 150.000,
                    'XAUUSD': 2000.00,
                    'AUDUSD': 0.65000,
                    'USDCHF': 0.90000,
                    'US30': 35000.00,
                    'NAS100': 18000.00,
                    'BTCUSD': 40000.00,
                    'ETHUSD': 2500.00
                }.get(symbol, 1.00000)
                price = price_approx
            
            # Calcular margen
            margin_required = (volume * contract_size * price) / leverage
            
            return {
                "margin_required": margin_required,
                "is_valid": True,
                "message": f"Margen requerido para {volume} lote(s): ${margin_required:.2f} USD",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando margen: {str(e)}")
            return {
                "margin_required": 0,
                "is_valid": False,
                "message": f"Error calculando margen: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de un símbolo.
        
        Args:
            symbol: Símbolo a consultar
            
        Returns:
            Dict[str, Any]: Información del símbolo
        """
        config = self._get_symbol_config(symbol)
        
        return {
            "symbol": symbol,
            "point": config.get('point', 0.00001),
            "digits": config.get('digits', 5),
            "min_volume": config.get('min_volume', self.min_volume),
            "max_volume": config.get('max_volume', self.max_volume),
            "volume_step": config.get('volume_step', 0.01),
            "min_distance_pips": config.get('min_distance_pips', 2),
            "spread": config.get('spread', 10),
            "valid": True
        }


# Factory function para crear el validador
def create_order_validator() -> OrderValidator:
    """
    Crea una instancia del validador de órdenes.
    
    Returns:
        OrderValidator: Instancia del validador
    """
    return OrderValidator()