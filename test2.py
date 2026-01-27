# test_mt5_orders_us500_corrected.py
"""
Script para probar la colocación de órdenes en MetaTrader 5.
Versión corregida con atributos correctos de MT5
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Agregar el directorio raíz al path para poder importar la configuración
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Importar configuración
from src.config.settings import *

# Importar MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("Error: MetaTrader5 no está instalado. Instala con: pip install MetaTrader5")
    sys.exit(1)

# Ajustar configuración para US500
US500_MIN_VOLUME = 0.1  # Volumen mínimo para índices como US500
US500_MAX_VOLUME = 10.0  # Volumen máximo típico
US500_VOLUME_STEP = 0.1  # Incremento de volumen

class MT5OrderTester:
    """Clase para probar órdenes en MT5 con ajustes para US500"""
    
    def __init__(self):
        self.connected = False
        self.symbol = DEFAULT_SYMBOL  # US500 por defecto
        self.account_info = None
        self.terminal_info = None
        
    def check_autotrading_enabled(self):
        """Verificar si AutoTrading está habilitado en MT5"""
        if not self.connected:
            return False
        
        self.terminal_info = mt5.terminal_info()
        if self.terminal_info is None:
            print("❌ No se pudo obtener información del terminal")
            return False
        
        trading_allowed = self.terminal_info.trade_allowed
        
        print(f"\n📊 Estado de trading del terminal:")
        print(f"   Trading permitido: {'✅ SÍ' if trading_allowed else '❌ NO'}")
        print(f"   Comunidad: {'✅ SÍ' if self.terminal_info.community_connection else '❌ NO'}")
        print(f"   Conexión: {'✅ CONECTADO' if self.terminal_info.connected else '❌ DESCONECTADO'}")
        print(f"   DLLs permitidas: {'✅ SÍ' if self.terminal_info.dlls_allowed else '❌ NO'}")
        print(f"   Trading por EA: {'✅ SÍ' if self.terminal_info.tradeapi_disabled == 0 else '❌ NO'}")
        
        if not trading_allowed:
            self.show_autotrading_instructions()
        
        return trading_allowed
    
    def show_autotrading_instructions(self):
        """Mostrar instrucciones para habilitar AutoTrading"""
        print("\n" + "="*70)
        print("⚠️  INSTRUCCIONES PARA HABILITAR AUTOTRADING")
        print("="*70)
        print("1. En MetaTrader 5:")
        print("   • Ve a 'Herramientas' → 'Opciones' → 'Expert Advisors'")
        print("   • Marca 'Permitir trading algorítmico'")
        print("   • Marca 'Permitir importación de DLL'")
        print("   • Haz clic en 'Aceptar'")
        print("\n2. Habilita el botón AutoTrading:")
        print("   • Busca el botón 'AutoTrading' en la barra de herramientas")
        print("   • Debe verse verde (○ → ●)")
        print("   • O presiona 'Ctrl + T'")
        print("\n3. Revisa el estado del símbolo:")
        print("   • Asegúrate de que 'US500' esté disponible en 'Observación de Mercado'")
        print("   • Si no está, haz clic derecho y 'Mostrar todo'")
        print("="*70 + "\n")
    
    def connect_to_mt5(self):
        """Conectar a MT5 usando la configuración"""
        print(f"\n🔗 Conectando a MT5...")
        print(f"   Login: {MT5_LOGIN}")
        print(f"   Server: {MT5_SERVER}")
        
        # Intentar conectar
        for attempt in range(MAX_CONNECTION_RETRIES):
            print(f"\n   Intento {attempt + 1} de {MAX_CONNECTION_RETRIES}...")
            
            if mt5.initialize(
                path=MT5_PATH,
                login=MT5_LOGIN,
                server=MT5_SERVER,
                password=MT5_PASSWORD,
                timeout=MT5_TIMEOUT,
                portable=False
            ):
                self.connected = True
                print("   ✅ Conexión exitosa a MT5")
                break
            else:
                error = mt5.last_error()
                print(f"   ❌ Error: {error}")
                
                if attempt < MAX_CONNECTION_RETRIES - 1:
                    print(f"   ⏳ Reintentando en {CONNECTION_RETRY_DELAY} segundos...")
                    time.sleep(CONNECTION_RETRY_DELAY)
        
        if not self.connected:
            # Probar rutas alternativas
            print(f"\n🔄 Probando rutas alternativas...")
            for alt_path in MT5_ALTERNATIVE_PATHS:
                print(f"   Probando: {alt_path}")
                if mt5.initialize(
                    path=alt_path,
                    login=MT5_LOGIN,
                    server=MT5_SERVER,
                    password=MT5_PASSWORD,
                    timeout=MT5_TIMEOUT,
                    portable=False
                ):
                    self.connected = True
                    print(f"   ✅ Conexión exitosa con ruta alternativa")
                    break
        
        if self.connected:
            self.account_info = mt5.account_info()
            if self.account_info:
                self.display_account_info()
            else:
                print("❌ No se pudo obtener información de la cuenta")
                self.connected = False
                return False
            
            # Verificar AutoTrading
            autotrading_ok = self.check_autotrading_enabled()
            
            if not autotrading_ok:
                print("\n⚠️  ADVERTENCIA: AutoTrading podría estar deshabilitado")
                print("   Puedes intentar colocar órdenes, pero podrían fallar")
                response = input("   ¿Continuar de todos modos? (s/n): ").lower()
                if response != 's':
                    print("❌ Operación cancelada por el usuario")
                    return False
            
            # Verificar símbolo US500
            symbol_ok = self.check_symbol_availability()
            
            if not symbol_ok:
                print("❌ Problemas con el símbolo US500")
                return False
        
        return self.connected
    
    def display_account_info(self):
        """Mostrar información de la cuenta"""
        print(f"\n" + "="*50)
        print("💰 INFORMACIÓN DE LA CUENTA")
        print("="*50)
        print(f"   Nombre: {self.account_info.name}")
        print(f"   Número: {self.account_info.login}")
        print(f"   Balance: ${self.account_info.balance:.2f}")
        print(f"   Equity: ${self.account_info.equity:.2f}")
        print(f"   Margen Libre: ${self.account_info.margin_free:.2f}")
        print(f"   Margen Utilizado: ${self.account_info.margin:.2f}")
        print(f"   Apalancamiento: 1:{self.account_info.leverage}")
        print(f"   Moneda: {self.account_info.currency}")
        print(f"   Trading permitido: {'✅ SÍ' if self.account_info.trade_allowed else '❌ NO'}")
        print(f"   Trading por Expert: {'✅ SÍ' if self.account_info.trade_expert else '❌ NO'}")
        print("="*50)
    
    def check_symbol_availability(self):
        """Verificar disponibilidad y configuración del símbolo US500"""
        print(f"\n📈 Verificando símbolo {self.symbol}...")
        
        symbol_info = mt5.symbol_info(self.symbol)
        
        if symbol_info is None:
            print(f"   ❌ Símbolo {self.symbol} no encontrado")
            print(f"   Intentando seleccionar...")
            
            if mt5.symbol_select(self.symbol, True):
                print(f"   ✅ Símbolo {self.symbol} seleccionado")
                symbol_info = mt5.symbol_info(self.symbol)
            else:
                print(f"   ❌ No se pudo seleccionar {self.symbol}")
                return False
        
        if not symbol_info.visible:
            print(f"   ⚠️  Símbolo no visible, seleccionando...")
            mt5.symbol_select(self.symbol, True)
        
        # Mostrar información detallada del símbolo
        print(f"   ✅ Símbolo disponible")
        print(f"\n   📊 Información de {self.symbol}:")
        print(f"      Bid: {symbol_info.bid:.1f}")
        print(f"      Ask: {symbol_info.ask:.1f}")
        print(f"      Spread: {(symbol_info.ask - symbol_info.bid):.1f}")
        print(f"      Volumen mínimo: {symbol_info.volume_min}")
        print(f"      Volumen máximo: {symbol_info.volume_max}")
        print(f"      Paso de volumen: {symbol_info.volume_step}")
        print(f"      Punto: {symbol_info.point}")
        print(f"      Dígitos: {symbol_info.digits}")
        print(f"      Spread flotante: {symbol_info.spread_float}")
        print(f"      Trading permitido: {'✅ SÍ' if symbol_info.trade_mode == 0 else '❌ NO'}")
        
        # Verificar volumen adecuado
        if symbol_info.volume_min > DEFAULT_LOT_SIZE:
            print(f"\n   ⚠️  ADVERTENCIA: Volumen mínimo es {symbol_info.volume_min}")
            print(f"      Usando {symbol_info.volume_min} como volumen por defecto")
        
        return True
    
    def get_appropriate_volume(self, requested_volume):
        """Obtener volumen apropiado según las especificaciones del símbolo"""
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return US500_MIN_VOLUME
        
        # Asegurar que el volumen esté dentro de los límites
        volume = max(requested_volume, symbol_info.volume_min)
        volume = min(volume, symbol_info.volume_max)
        
        # Redondear al paso apropiado
        step = symbol_info.volume_step
        if step > 0:
            volume = round(volume / step) * step
        
        return volume
    
    def place_buy_order(self, volume=US500_MIN_VOLUME, stop_loss_pips=None, take_profit_pips=None):
        """Colocar una orden de compra para US500"""
        if not self.connected:
            print("❌ No conectado a MT5")
            return False
        
        # Verificar símbolo
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Símbolo {self.symbol} no disponible")
            return False
        
        if not symbol_info.visible:
            mt5.symbol_select(self.symbol, True)
            symbol_info = mt5.symbol_info(self.symbol)
        
        # Ajustar volumen
        adjusted_volume = self.get_appropriate_volume(volume)
        if adjusted_volume != volume:
            print(f"⚠️  Volumen ajustado de {volume} a {adjusted_volume}")
        
        # Preparar orden
        price = symbol_info.ask
        point = symbol_info.point
        
        # Calcular SL y TP (US500 usa 1 punto = 0.1 en precio)
        sl_price = 0
        tp_price = 0
        
        if stop_loss_pips:
            # Para US500, cada pip son 10 puntos
            sl_price = price - (stop_loss_pips * point * 10)
        
        if take_profit_pips:
            tp_price = price + (take_profit_pips * point * 10)
        
        # Crear solicitud
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": adjusted_volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": DEFAULT_SLIPPAGE,  # En puntos, no pips
            "magic": 1001,
            "comment": f"BUY US500 {datetime.now().strftime('%H:%M')}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        print(f"\n🟢 ENVIANDO ORDEN DE COMPRA")
        print(f"   Símbolo: {self.symbol}")
        print(f"   Volumen: {adjusted_volume}")
        print(f"   Precio: {price:.1f}")
        if stop_loss_pips:
            print(f"   SL: {sl_price:.1f} ({stop_loss_pips} pips)")
        if take_profit_pips:
            print(f"   TP: {tp_price:.1f} ({take_profit_pips} pips)")
        
        # Enviar orden
        result = mt5.order_send(request)
        
        return self.handle_order_result(result, "COMPRA")
    
    def place_sell_order(self, volume=US500_MIN_VOLUME, stop_loss_pips=None, take_profit_pips=None):
        """Colocar una orden de venta para US500"""
        if not self.connected:
            print("❌ No conectado a MT5")
            return False
        
        # Verificar símbolo
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Símbolo {self.symbol} no disponible")
            return False
        
        if not symbol_info.visible:
            mt5.symbol_select(self.symbol, True)
            symbol_info = mt5.symbol_info(self.symbol)
        
        # Ajustar volumen
        adjusted_volume = self.get_appropriate_volume(volume)
        if adjusted_volume != volume:
            print(f"⚠️  Volumen ajustado de {volume} a {adjusted_volume}")
        
        # Preparar orden
        price = symbol_info.bid
        point = symbol_info.point
        
        # Calcular SL y TP
        sl_price = 0
        tp_price = 0
        
        if stop_loss_pips:
            sl_price = price + (stop_loss_pips * point * 10)
        
        if take_profit_pips:
            tp_price = price - (take_profit_pips * point * 10)
        
        # Crear solicitud
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": adjusted_volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": DEFAULT_SLIPPAGE,
            "magic": 1002,
            "comment": f"SELL US500 {datetime.now().strftime('%H:%M')}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        print(f"\n🔴 ENVIANDO ORDEN DE VENTA")
        print(f"   Símbolo: {self.symbol}")
        print(f"   Volumen: {adjusted_volume}")
        print(f"   Precio: {price:.1f}")
        if stop_loss_pips:
            print(f"   SL: {sl_price:.1f} ({stop_loss_pips} pips)")
        if take_profit_pips:
            print(f"   TP: {tp_price:.1f} ({take_profit_pips} pips)")
        
        # Enviar orden
        result = mt5.order_send(request)
        
        return self.handle_order_result(result, "VENTA")
    
    def handle_order_result(self, result, order_type):
        """Manejar el resultado de una orden"""
        if result is None:
            error = mt5.last_error()
            print(f"❌ Error al enviar orden: {error}")
            
            # Manejar errores específicos
            error_code = error[0] if isinstance(error, tuple) and len(error) > 0 else 0
            
            if error_code == 10016:  # AutoTrading disabled
                print("\n❌ ERROR: AutoTrading deshabilitado")
                print("   Por favor, habilita AutoTrading en MT5:")
                print("   1. Herramientas → Opciones → Expert Advisors")
                print("   2. Marca 'Permitir trading algorítmico'")
                print("   3. Ctrl + T para activar AutoTrading")
            elif error_code == 10019:  # Trade disabled
                print("\n❌ ERROR: Trading deshabilitado")
                print("   Verifica que el trading esté habilitado en la cuenta")
            elif error_code == 10013:  # Invalid volume
                print("\n❌ ERROR: Volumen inválido")
                print("   Verifica el volumen mínimo del símbolo")
            
            return False
        
        print(f"\n📊 RESULTADO DE LA ORDEN:")
        print(f"   Código: {result.retcode}")
        
        # Decodificar resultado
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ✅ ORDEN DE {order_type} EXITOSA")
            print(f"   ID Orden: {result.order}")
            print(f"   ID Operación: {result.deal}")
            print(f"   Volumen ejecutado: {result.volume}")
            print(f"   Precio ejecutado: {result.price:.1f}")
            
            # Calcular margen requerido aproximado
            if hasattr(result, 'margin_required'):
                print(f"   Margen requerido: ${result.margin_required:.2f}")
            
            return True
        else:
            print(f"   ❌ ORDEN RECHAZADA")
            print(f"   Razón: {result.comment}")
            
            # Errores comunes de MT5
            error_messages = {
                10004: "Requote - precio cambiado",
                10006: "Rechazada por el dealer",
                10007: "Cancelada por el cliente",
                10008: "Volumen insuficiente",
                10009: "Sin conexión",
                10010: "Timeout",
                10012: "Orden inválida",
                10013: "Volumen inválido",
                10014: "Precio inválido",
                10015: "Símbolo inválido",
                10016: "AutoTrading deshabilitado",
                10017: "No hay suficientes fondos",
                10018: "Mercado cerrado",
                10019: "Trade deshabilitado",
                10020: "Prohibido",
                10021: "Margen insuficiente",
                10022: "Posición no encontrada",
                10023: "Límite de operaciones alcanzado",
                10024: "Límite de volumen alcanzado",
                10025: "Cuenta bloqueada",
                10026: "Cuenta invalidada",
                10027: "Hedge prohibido",
                10028: "Ordenes prohibidas",
                10029: "Demasiadas solicitudes",
                10030: "Cambios no permitidos",
                10031: "Trade contexto ocupado",
                10032: "Expiración denegada",
                10033: "Demasiadas órdenes",
                10034: "No hay precios",
                10035: "Precio inválido",
                10036: "Símbolo no válido",
                10038: "Orden no válida",
                10039: "Volumen demasiado pequeño",
                10040: "Volumen demasiado grande",
            }
            
            if result.retcode in error_messages:
                print(f"   Detalle: {error_messages[result.retcode]}")
            
            return False
    
    def get_open_positions(self):
        """Obtener posiciones abiertas"""
        if not self.connected:
            print("❌ No conectado a MT5")
            return []
        
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions is None:
            positions = []
        
        if len(positions) == 0:
            print(f"\n📭 No hay posiciones abiertas en {self.symbol}")
            return []
        
        print(f"\n📋 POSICIONES ABIERTAS EN {self.symbol} ({len(positions)})")
        print("="*60)
        
        total_profit = 0
        for i, pos in enumerate(positions, 1):
            profit_color = "🟢" if pos.profit >= 0 else "🔴"
            direction = "COMPRA" if pos.type == 0 else "VENTA"
            
            print(f"\n#{i} {profit_color} {direction}")
            print(f"   Ticket: {pos.ticket}")
            print(f"   Volumen: {pos.volume}")
            print(f"   Precio apertura: {pos.price_open:.1f}")
            print(f"   Precio actual: {pos.price_current:.1f}")
            print(f"   SL: {pos.sl:.1f}")
            print(f"   TP: {pos.tp:.1f}")
            print(f"   Beneficio: ${pos.profit:.2f}")
            print(f"   Swap: ${pos.swap:.2f}")
            print(f"   Comisión: ${pos.commission:.2f}")
            print(f"   Abierta: {datetime.fromtimestamp(pos.time)}")
            
            total_profit += pos.profit
        
        print("\n" + "="*60)
        print(f"💰 BENEFICIO TOTAL: ${total_profit:.2f}")
        
        return positions
    
    def close_position(self, ticket):
        """Cerrar una posición específica"""
        if not self.connected:
            print("❌ No conectado a MT5")
            return False
        
        # Buscar la posición
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            print(f"❌ No se encontró la posición con ticket {ticket}")
            return False
        
        position = position[0]
        
        print(f"\n⚠️  CERRANDO POSICIÓN #{ticket}")
        print(f"   Símbolo: {position.symbol}")
        print(f"   Tipo: {'COMPRA' if position.type == 0 else 'VENTA'}")
        print(f"   Volumen: {position.volume}")
        print(f"   Beneficio actual: ${position.profit:.2f}")
        
        response = input("¿Confirmar cierre? (s/n): ").lower()
        if response != 's':
            print("❌ Operación cancelada")
            return False
        
        # Preparar orden de cierre
        tick = mt5.symbol_info_tick(position.symbol)
        
        if position.type == 0:  # BUY position -> close with SELL
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:  # SELL position -> close with BUY
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": DEFAULT_SLIPPAGE,
            "magic": 1003,
            "comment": f"CLOSE {datetime.now().strftime('%H:%M')}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ✅ Posición #{ticket} cerrada exitosamente")
            print(f"   Precio de cierre: {result.price:.1f}")
            print(f"   Beneficio final: ${position.profit:.2f}")
            return True
        else:
            print(f"   ❌ Error al cerrar posición #{ticket}")
            if result:
                print(f"   Razón: {result.comment}")
            return False
    
    def close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        positions = self.get_open_positions()
        
        if not positions:
            return True
        
        print(f"\n⚠️  CERRANDO {len(positions)} POSICIÓN(ES)")
        
        response = input("¿Confirmar cierre de todas las posiciones? (s/n): ").lower()
        if response != 's':
            print("❌ Operación cancelada")
            return False
        
        all_closed = True
        for pos in positions:
            if not self.close_position(pos.ticket):
                all_closed = False
        
        return all_closed
    
    def test_safe_orders(self):
        """Probar órdenes de forma segura con volúmenes mínimos"""
        print("\n" + "="*60)
        print("🧪 PRUEBAS SEGURAS DE ÓRDENES")
        print("="*60)
        
        # 1. Obtener precio actual
        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            print(f"❌ No se pudo obtener información de {self.symbol}")
            return
        
        print(f"\n📈 Precio actual {self.symbol}:")
        print(f"   Bid: {symbol_info.bid:.1f}")
        print(f"   Ask: {symbol_info.ask:.1f}")
        print(f"   Spread: {(symbol_info.ask - symbol_info.bid):.1f}")
        print(f"   Volumen mínimo: {symbol_info.volume_min}")
        
        # 2. Probar compra mínima
        print("\n1. Probando COMPRA mínima...")
        success_buy = self.place_buy_order(volume=symbol_info.volume_min)
        
        time.sleep(2)
        
        # 3. Probar venta mínima
        print("\n2. Probando VENTA mínima...")
        success_sell = self.place_sell_order(volume=symbol_info.volume_min)
        
        # 4. Mostrar resumen
        print("\n" + "="*60)
        print("📊 RESUMEN DE PRUEBAS")
        print("="*60)
        print(f"   Compra: {'✅ EXITOSA' if success_buy else '❌ FALLIDA'}")
        print(f"   Venta: {'✅ EXITOSA' if success_sell else '❌ FALLIDA'}")
        
        # 5. Mostrar posiciones
        self.get_open_positions()

def main():
    """Función principal"""
    print("="*70)
    print("🤖 TEST DE ÓRDENES MT5 - ESPECIAL US500 (CORREGIDO)")
    print("="*70)
    print(f"Volumen mínimo recomendado: {US500_MIN_VOLUME} lotes")
    print("="*70)
    
    if not MT5_AVAILABLE:
        print("❌ Instala MetaTrader5: pip install MetaTrader5")
        return
    
    tester = MT5OrderTester()
    
    try:
        # Conectar
        if not tester.connect_to_mt5():
            print("❌ No se pudo conectar a MT5")
            return
        
        # Menú principal
        while True:
            print("\n" + "="*50)
            print("📋 MENÚ PRINCIPAL")
            print("="*50)
            print("1. Verificar estado y conexión")
            print("2. Prueba COMPRA (volumen mínimo)")
            print("3. Prueba VENTA (volumen mínimo)")
            print("4. COMPRA con SL/TP personalizado")
            print("5. VENTA con SL/TP personalizado")
            print("6. Ver posiciones abiertas")
            print("7. Cerrar posición específica")
            print("8. Cerrar todas las posiciones")
            print("9. Ejecutar pruebas seguras")
            print("10. Instrucciones AutoTrading")
            print("0. Salir")
            print("="*50)
            
            try:
                choice = input("\nSeleccione opción (0-10): ")
                
                if choice == '1':
                    tester.check_autotrading_enabled()
                    tester.check_symbol_availability()
                    
                elif choice == '2':
                    # Obtener volumen mínimo real del símbolo
                    symbol_info = mt5.symbol_info(tester.symbol)
                    if symbol_info:
                        min_volume = symbol_info.volume_min
                        print(f"\n📊 Volumen mínimo de {tester.symbol}: {min_volume}")
                        tester.place_buy_order(volume=min_volume)
                    else:
                        tester.place_buy_order()
                        
                elif choice == '3':
                    symbol_info = mt5.symbol_info(tester.symbol)
                    if symbol_info:
                        min_volume = symbol_info.volume_min
                        print(f"\n📊 Volumen mínimo de {tester.symbol}: {min_volume}")
                        tester.place_sell_order(volume=min_volume)
                    else:
                        tester.place_sell_order()
                        
                elif choice == '4':
                    try:
                        sl = int(input("Stop Loss (pips): "))
                        tp = int(input("Take Profit (pips): "))
                        volume = float(input(f"Volumen (ej: {US500_MIN_VOLUME}): ") or US500_MIN_VOLUME)
                        tester.place_buy_order(volume=volume, stop_loss_pips=sl, take_profit_pips=tp)
                    except ValueError:
                        print("❌ Entrada inválida. Usa números.")
                        
                elif choice == '5':
                    try:
                        sl = int(input("Stop Loss (pips): "))
                        tp = int(input("Take Profit (pips): "))
                        volume = float(input(f"Volumen (ej: {US500_MIN_VOLUME}): ") or US500_MIN_VOLUME)
                        tester.place_sell_order(volume=volume, stop_loss_pips=sl, take_profit_pips=tp)
                    except ValueError:
                        print("❌ Entrada inválida. Usa números.")
                        
                elif choice == '6':
                    tester.get_open_positions()
                    
                elif choice == '7':
                    try:
                        ticket = int(input("Ticket de la posición a cerrar: "))
                        tester.close_position(ticket)
                    except ValueError:
                        print("❌ Ticket inválido. Debe ser un número.")
                        
                elif choice == '8':
                    tester.close_all_positions()
                    
                elif choice == '9':
                    tester.test_safe_orders()
                    
                elif choice == '10':
                    tester.show_autotrading_instructions()
                    
                elif choice == '0':
                    print("\n👋 Saliendo del programa...")
                    break
                    
                else:
                    print("❌ Opción inválida")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⚠️  Operación cancelada por el usuario")
                continue
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester.connected:
            print("\n🔌 Desconectando de MT5...")
            mt5.shutdown()

if __name__ == "__main__":
    main()