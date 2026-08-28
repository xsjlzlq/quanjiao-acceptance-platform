import os

for root, dirs, files in os.walk('frontend/src/views'):
    for file in files:
        if file.endswith('.vue'):
            filepath = os.path.join(root, file)
            try:
                # Read assuming utf-8-sig (which handles BOM) or gb18030
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                # Rewrite strictly as utf-8 without BOM
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed {filepath}")
            except Exception as e:
                try:
                    with open(filepath, 'r', encoding='gb18030') as f:
                        content = f.read()
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Fixed {filepath} from GBK")
                except Exception as e:
                    print(f"Failed {filepath}: {e}")
