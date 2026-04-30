#!/usr/bin/env python3
"""
Script pentru eliminarea referințelor AI din Prissma Studio
Autor: Alb Alexandru
"""

import os
import re
import sys

def find_ai_references(directory):
    """Găsește toate referințele la AI/Gemini în proiect"""

    patterns = [
        r'gemini',
        r'Gemini', 
        r'google\.generativeai',
        r'genai\.',
        r'AI Assistant',
        r'AI Smart Search',
        r'Analiză AI',
        r'Analiza AI',
        r'generate_ai_description',
        r'ai_smart_search',
        r'api_ai_search',
        r'ai_search',
        r'ai_worker',
        r'google-generativeai',
    ]

    extensions = ['.py', '.html', '.js', '.css', '.txt', '.sh', '.md']

    matches = []

    for root, dirs, files in os.walk(directory):
        if '.git' in root:
            continue

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')

                        for i, line in enumerate(lines, 1):
                            for pattern in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    matches.append({
                                        'file': filepath,
                                        'line': i,
                                        'content': line.strip(),
                                        'pattern': pattern
                                    })
                                    break
                except Exception as e:
                    print(f"Eroare la citirea {filepath}: {e}")

    return matches

def main():
    if len(sys.argv) < 2:
        print("Utilizare: python remove_ai.py <cale_catre_proiect>")
        sys.exit(1)

    project_dir = sys.argv[1]

    if not os.path.exists(project_dir):
        print(f"Directorul {project_dir} nu exista!")
        sys.exit(1)

    print(f"Caut referinte AI in: {project_dir}")
    print("=" * 60)

    matches = find_ai_references(project_dir)

    if not matches:
        print("Nu am gasit referinte la AI/Gemini!")
        return

    by_file = {}
    for m in matches:
        f = m['file']
        if f not in by_file:
            by_file[f] = []
        by_file[f].append(m)

    print(f"\nAm gasit {len(matches)} referinte in {len(by_file)} fisiere:\n")

    for filepath, file_matches in by_file.items():
        rel_path = os.path.relpath(filepath, project_dir)
        print(f"\n📄 {rel_path}")
        print("-" * 40)
        for m in file_matches:
            print(f"  Linia {m['line']}: {m['content'][:80]}")

    print("\n" + "=" * 60)
    print("IMPORTANT: Acest script DOAR detecteaza. Trebuie sa editezi manual!")
    print("=" * 60)

if __name__ == '__main__':
    main()
