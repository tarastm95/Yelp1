#!/usr/bin/env python3
"""
🔧 Fix except block indentation
"""

def fix_except_indent():
    """Виправляє індентацію except блоку"""
    
    with open('backend/webhooks/vector_search_service.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Знаходимо проблемний except на лінії ~222
    for i, line in enumerate(lines):
        if 'except Exception as e:' in line and line.startswith('                except'):
            # Виправляємо індентацію: 16 пробілів → 8 пробілів
            lines[i] = '        except Exception as e:\n'
            print(f"✅ Fixed line {i+1}: except block indentation")
            
        # Також виправляємо наступні рядки в except блоці
        elif i < len(lines) - 1 and lines[i-1].strip() == 'except Exception as e:' and line.startswith('            logger.error'):
            lines[i] = '            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")\n'
            print(f"✅ Fixed line {i+1}: logger.error indentation")
            
        elif i < len(lines) - 1 and 'logger.exception("Vector search error details")' in line and line.startswith('            '):
            lines[i] = '            logger.exception("Vector search error details")\n'
            print(f"✅ Fixed line {i+1}: logger.exception indentation")
            
        elif i < len(lines) - 1 and 'return []' in line and line.startswith('            ') and 'Vector search error' in lines[i-1]:
            lines[i] = '            return []\n'
            print(f"✅ Fixed line {i+1}: return [] indentation")
    
    # Записуємо назад
    with open('backend/webhooks/vector_search_service.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ Fixed except block indentation!")

if __name__ == '__main__':
    fix_except_indent()
