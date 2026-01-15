# test_easy.py
import os
import sys

# 1. Agregar la carpeta actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 PRUEBA FÁCIL DE CONEXIÓN MT5")
print("=" * 50)

# 2. Probar importaciones paso a paso
print("1. Probando importaciones...")
try:
    # Primero probar MetaTrader5 directamente
    import MetaTrader5 as mt5
    print(f"✅ MetaTrader5 importado (v{mt5.__version__})")
    
    # Ahora probar tus módulos
    try:
        # Intentar importar desde src
        from src.infrastructure.persistence.mt5.mt5_connection import create_mt5_connection
        print("✅ mt5_connection importado")
    except ImportError as e:
        print(f"⚠️  mt5_connection error: {e}")
        print("   Intentando arreglar estructura...")
        
        # Crear __init__.py si faltan
        folders_to_check = [
            "src",
            "src/infrastructure", 
            "src/infrastructure/persistence",
            "src/infrastructure/persistence/mt5"
        ]
        
        for folder in folders_to_check:
            init_file = os.path.join(folder, "__init__.py")
            if not os.path.exists(init_file):
                os.makedirs(os.path.dirname(init_file), exist_ok=True)
                with open(init_file, "w") as f:
                    f.write("# Auto-generated\n")
                print(f"   Creado: {init_file}")
    
    # Reintentar importación
    from src.infrastructure.persistence.mt5.mt5_connection import create_mt5_connection
    print("✅ mt5_connection importado (2do intento)")
    
except ImportError as e:
    print(f"❌ Error crítico: {e}")
    print("\n💡 SOLUCIÓN RÁPIDA:")
    print("Ejecuta este comando para crear la estructura completa:")
    print("""
import os
import sys

# Crear estructura de carpetas
folders = [
    "src",
    "src/application",
    "src/application/use_cases",
    "src/config",
    "src/domain",
    "src/domain/entities",
    "src/domain/repositories",
    "src/domain/repositories/abstract",
    "src/infrastructure",
    "src/infrastructure/persistence",
    "src/infrastructure/persistence/mt5",
    "src/presentation"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    init_file = os.path.join(folder, "__init__.py")
    with open(init_file, "w") as f:
        f.write("# Auto-generated\\n")
    print(f"Creado: {folder}/__init__.py")

print("✅ Estructura creada")
""")
    sys.exit(1)

print("\n2. Probando conexión directa a MT5...")
try:
    # Prueba directa sin tus módulos
    if mt5.initialize():
        print("✅ MT5 inicializado")
        
        # Login con credenciales hardcodeadas
        authorized = mt5.login(
            login=61454844,
            password="b;hsd6vetP",
            server="Pepperstone-Demo"
        )
        
        if authorized:
            print("✅ Login exitoso")
            account = mt5.account_info()
            print(f"   Cuenta: {account.login}")
            print(f"   Broker: {account.server}")
            print(f"   Balance: ${account.balance:.2f}")
            
            # Prueba obtener datos
            print("\n3. Probando obtención de datos...")
            rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 5)
            if rates is not None:
                print(f"✅ Datos obtenidos: {len(rates)} velas")
                print(f"   Último close: {rates[-1][4]}")
            else:
                print("❌ No se pudieron obtener datos")
            
            mt5.shutdown()
            print("\n✅ MT5 cerrado correctamente")
        else:
            error = mt5.last_error()
            print(f"❌ Login falló: {error}")
            mt5.shutdown()
    else:
        error = mt5.last_error()
        print(f"❌ MT5 no se pudo inicializar: {error}")
        
except Exception as e:
    print(f"❌ Error durante la prueba: {e}")

print("\n" + "=" * 50)
print("✨ PRUEBA COMPLETADA")