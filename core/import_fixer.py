# core/import_fixer.py
"""Автоматическое создание недостающих функций при импорте."""
import os
import re

def fix_missing_imports():
    """
    Проверяет bot.py на импорты из core.rpg_* и создаёт недостающие функции.
    """
    if not os.path.exists("bot.py"):
        return
    
    with open("bot.py", "r", encoding="utf-8") as f:
        bot_code = f.read()
    
    # Находим все импорты из core.rpg_*
    import_lines = [l.strip() for l in bot_code.split('\n') 
                   if l.strip().startswith('from core.rpg_')]
    
    for line in import_lines:
        # from core.rpg_combat import func1, func2
        match = re.match(r'from (core\.rpg_\w+) import (.+)', line)
        if not match:
            continue
        
        module_name = match.group(1)  # core.rpg_combat
        funcs_str = match.group(2)    # func1, func2
        
        # Разбираем имена функций
        funcs = [f.strip() for f in funcs_str.split(',')]
        
        # Путь к файлу модуля
        module_path = module_name.replace('.', '/') + '.py'
        
        if not os.path.exists(module_path):
            # Создаём новый модуль с заглушками
            with open(module_path, "w", encoding="utf-8") as f:
                f.write(f"# {module_name}.py — Создано автоматически\n")
                f.write("import random\n\n")
                for func in funcs:
                    f.write(f"def {func}(*args, **kwargs):\n")
                    f.write(f"    return 'Заглушка {func} — будет улучшено Дарвином'\n\n")
            print(f"✅ Создан модуль {module_path} с функциями: {funcs}")
            continue
        
        # Модуль существует — проверяем функции
        with open(module_path, "r", encoding="utf-8") as f:
            module_code = f.read()
        
        missing = []
        for func in funcs:
            if f"def {func}(" not in module_code:
                missing.append(func)
        
        if missing:
            # Добавляем недостающие функции в конец модуля
            with open(module_path, "a", encoding="utf-8") as f:
                f.write("\n\n# Автозаглушки — Дарвин улучшит\n")
                for func in missing:
                    f.write(f"def {func}(*args, **kwargs):\n")
                    f.write(f"    return 'Заглушка {func} — будет улучшено Дарвином'\n\n")
            print(f"✅ Добавлены заглушки в {module_path}: {missing}")


def fix_all_imports():
    """Проверяет и исправляет импорты во всех модулях."""
    fix_missing_imports()
    
    # Проверяем модули на импорты из core
    for root, dirs, files in os.walk("core"):
        for file in files:
            if file.endswith(".py") and file.startswith("rpg_"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Ищем импорты из других core.rpg_* модулей
                import_lines = [l for l in code.split('\n') 
                              if 'from core.rpg_' in l and 'import' in l]
                
                for line in import_lines:
                    match = re.match(r'from (core\.rpg_\w+) import (.+)', line)
                    if not match:
                        continue
                    
                    dep_module = match.group(1)
                    funcs = [f.strip() for f in match.group(2).split(',')]
                    
                    dep_path = dep_module.replace('.', '/') + '.py'
                    if not os.path.exists(dep_path):
                        continue
                    
                    with open(dep_path, "r", encoding="utf-8") as f2:
                        dep_code = f2.read()
                    
                    missing = [f for f in funcs if f"def {f}(" not in dep_code]
                    if missing:
                        with open(dep_path, "a", encoding="utf-8") as f2:
                            f2.write(f"\n# Автозаглушка для {file}\n")
                            for func in missing:
                                f2.write(f"def {func}(*args, **kwargs):\n")
                                f2.write(f"    return 'Заглушка {func} — будет улучшено'\n\n")