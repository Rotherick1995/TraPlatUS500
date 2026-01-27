import MetaTrader5 as mt5
from datetime import datetime

def diagnose_symbol(symbol_name="US500"):
    """Diagnóstico completo del símbolo"""
    
    if not mt5.initialize():
        print("❌ Error conectando a MT5")
        return
    
    print(f"\n🔍 Diagnóstico para: {symbol_name}")
    print("-" * 50)
    
    # 1. Verificar si existe
    symbol_info = mt5.symbol_info(symbol_name)
    if symbol_info is None:
        print(f"❌ Símbolo '{symbol_name}' no encontrado")
        
        # Buscar alternativas
        all_symbols = mt5.symbols_get()
        similar = [s.name for s in all_symbols if "500" in s.name or "SPX" in s.name]
        print(f"🔎 Símbolos similares: {similar}")
        
    else:
        # 2. Información detallada
        print(f"✅ Símbolo existe")
        print(f"   Nombre completo: {symbol_info.name}")
        print(f"   Descripción: {symbol_info.description}")
        print(f"   Punto: {symbol_info.point}")
        print(f"   Dígitos: {symbol_info.digits}")
        
        # 3. Estado de trading
        print(f"\n📊 Estado de trading:")
        print(f"   Trade Mode: {symbol_info.trade_mode}")
        print(f"   Trade Execution: {symbol_info.trade_execution}")
        print(f"   Bid: {symbol_info.bid}")
        print(f"   Ask: {symbol_info.ask}")
        print(f"   Time: {datetime.now()}")
        
        # 4. Intentar seleccionar
        print(f"\n🔧 Intentando seleccionar símbolo...")
        if mt5.symbol_select(symbol_name, True):
            print(f"   ✅ Símbolo seleccionado")
        else:
            print(f"   ❌ No se pudo seleccionar")
            
        # 5. Verificar propiedades
        print(f"\n⚙️ Propiedades del símbolo:")
        print(f"   Visible: {symbol_info.visible}")
        print(f"   Session Quotes: {symbol_info.session_quotes}")
        print(f"   Session Trading: {symbol_info.session_trading}")
    
    mt5.shutdown()

# Ejecutar diagnóstico
diagnose_symbol("US500")