#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración del bot sin ejecutarlo.
"""

import os
import json
from pathlib import Path


def check_file(filepath, required=True):
    """Verificar si un archivo existe."""
    exists = Path(filepath).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    req_text = "(requerido)" if required else "(opcional)"
    print(f"{status} {filepath} {req_text}")
    return exists


def check_env_file():
    """Verificar archivo .env."""
    print("\n📋 Verificando archivo .env...")
    
    if not check_file(".env", required=True):
        print("   → Crea el archivo .env desde .env.example")
        return False
    
    # Leer y verificar variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["MATRIX_HOMESERVER", "MATRIX_USER_ID", "MATRIX_PASSWORD"]
    all_ok = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value and value != f"your_{var.lower()}_here":
            print(f"   ✅ {var} configurado")
        else:
            print(f"   ❌ {var} no configurado o usa valor por defecto")
            all_ok = False
    
    return all_ok


def check_json_file(filepath, required_keys=None):
    """Verificar archivo JSON."""
    if not check_file(filepath, required=True):
        return False
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        print(f"   ✅ JSON válido")
        
        if required_keys:
            for key in required_keys:
                if key in data:
                    count = len(data[key]) if isinstance(data[key], (dict, list)) else 1
                    print(f"   ✅ '{key}': {count} elemento(s)")
                else:
                    print(f"   ❌ Falta clave '{key}'")
                    return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"   ❌ Error de JSON: {e}")
        return False


def check_dependencies():
    """Verificar dependencias de Python."""
    print("\n📦 Verificando dependencias...")
    
    required_packages = [
        ("nio", "matrix-nio"),
        ("dotenv", "python-dotenv"),
        ("genai", "google-genai"),
    ]
    
    all_ok = True
    for module, package in required_packages:
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} no instalado")
            all_ok = False
    
    return all_ok


def check_users_config():
    """Verificar configuración de usuarios."""
    print("\n👥 Verificando users.json...")
    
    if not check_json_file("users.json", required_keys=["users"]):
        return False
    
    with open("users.json", 'r') as f:
        data = json.load(f)
    
    users = data.get("users", {})
    
    for user_id, config in users.items():
        print(f"\n   Usuario: {user_id}")
        
        if config.get("ai_enabled"):
            api_key = config.get("api_key", "")
            model = config.get("model", "")
            
            if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
                print(f"      ✅ API key configurada")
            else:
                print(f"      ⚠️  API key no configurada (IA no funcionará)")
            
            if model:
                print(f"      ✅ Modelo: {model}")
            else:
                print(f"      ⚠️  Sin modelo especificado")
        else:
            print(f"      ℹ️  IA deshabilitada para este usuario")
    
    return True


def check_commands_config():
    """Verificar configuración de comandos."""
    print("\n⚙️  Verificando commands.json...")
    
    if not check_json_file("commands.json", required_keys=["commands"]):
        return False
    
    with open("commands.json", 'r') as f:
        data = json.load(f)
    
    commands = data.get("commands", {})
    print(f"   ℹ️  {len(commands)} comando(s) configurado(s)")
    
    for cmd, config in commands.items():
        if config.get("type") == "shell" and config.get("script"):
            script = config["script"]
            # Verificar si es un comando del sistema o un archivo
            if "/" in script:
                if Path(script).exists():
                    print(f"   ✅ {cmd}: {script}")
                else:
                    print(f"   ⚠️  {cmd}: Script {script} no encontrado")
    
    return True


def main():
    """Función principal."""
    print("🔍 Verificador de Configuración del Bot de Matrix")
    print("=" * 50)
    
    # Cambiar al directorio del script
    os.chdir(Path(__file__).parent)
    
    all_checks = []
    
    # Verificar archivos básicos
    print("\n📁 Verificando archivos del proyecto...")
    all_checks.append(check_file("bot.py", required=True))
    all_checks.append(check_file("command_handler.py", required=True))
    all_checks.append(check_file("ai_handler.py", required=True))
    all_checks.append(check_file("requirements.txt", required=True))
    
    # Verificar archivos de configuración
    all_checks.append(check_env_file())
    all_checks.append(check_users_config())
    all_checks.append(check_commands_config())
    
    # Verificar dependencias
    all_checks.append(check_dependencies())
    
    # Verificar directorio store
    print("\n📂 Verificando directorios...")
    store_path = os.getenv("STORE_PATH", "./store")
    check_file(store_path, required=False)
    
    # Resumen final
    print("\n" + "=" * 50)
    if all(all_checks):
        print("✅ ¡Todas las verificaciones pasaron!")
        print("\n▶️  Puedes ejecutar el bot con: python bot.py")
    else:
        print("❌ Hay problemas con la configuración")
        print("\n📖 Revisa el README.md para más información")
        print("🔧 Ejecuta setup.sh para configuración inicial")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación cancelada")
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
