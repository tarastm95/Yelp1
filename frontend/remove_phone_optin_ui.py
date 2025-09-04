#!/usr/bin/env python3
"""
Видаляє Phone Opt-In налаштування з фронтенд UI
"""

def remove_phone_optin_ui():
    """
    Видаляє Phone Opt-In з AutoResponseSettings UI
    """
    
    file_path = "src/AutoResponseSettings.tsx"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    # 1. Видаляємо phoneOptIn state
    old_state = "  const [phoneOptIn, setPhoneOptIn] = useState(false);"
    if old_state in content:
        content = content.replace(old_state, "  // phoneOptIn removed - merged with No Phone scenario")
        changes_made.append("✅ Removed phoneOptIn state")
    
    # 2. Оновлюємо Tabs value логіку
    old_tabs_value = "value={phoneOptIn ? 'opt' : phoneAvailable ? 'text' : 'no'}"
    new_tabs_value = "value={phoneAvailable ? 'text' : 'no'}"
    
    if old_tabs_value in content:
        content = content.replace(old_tabs_value, new_tabs_value)
        changes_made.append("✅ Updated Tabs value logic")
    
    # 3. Спрощуємо onChange логіку
    old_onchange = '''                onChange={(_, v) => {
                  if (v === 'opt') {
                    setPhoneOptIn(true);
                    setPhoneAvailable(false);
                  } else if (v === 'text') {
                    setPhoneOptIn(false);
                    setPhoneAvailable(true);
                  } else {
                    setPhoneOptIn(false);
                    setPhoneAvailable(false);
                  }
                }}'''
    
    new_onchange = '''                onChange={(_, v) => {
                  if (v === 'text') {
                    setPhoneAvailable(true);
                  } else {
                    setPhoneAvailable(false);
                  }
                }}'''
    
    if old_onchange in content:
        content = content.replace(old_onchange, new_onchange)
        changes_made.append("✅ Simplified onChange logic")
    
    # 4. Видаляємо Opt-In Phone tab
    old_optin_tab = '''                <Tab
                  icon={<ContactPhoneIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Opt-In Phone"
                  value="opt"
                />'''
    
    if old_optin_tab in content:
        content = content.replace(old_optin_tab, "")
        changes_made.append("✅ Removed Opt-In Phone tab")
    
    # 5. Оновлюємо всі API виклики (видаляємо phone_opt_in параметр)
    # loadSettings
    old_load_params = '''    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');'''
    
    new_load_params = '''    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');'''
    
    content = content.replace(old_load_params, new_load_params)
    if old_load_params in content:
        changes_made.append("✅ Updated API parameters")
    
    # 6. Оновлюємо useEffect dependency
    old_dependency = "  }, [selectedBusiness, phoneOptIn, phoneAvailable]);"
    new_dependency = "  }, [selectedBusiness, phoneAvailable]);  // phoneOptIn removed"
    
    if old_dependency in content:
        content = content.replace(old_dependency, new_dependency)
        changes_made.append("✅ Updated useEffect dependencies")
    
    # 7. Замінюємо всі інші phoneOptIn використання
    content = content.replace("phoneOptIn ? 'true' : 'false'", "'false'  // Phone opt-in merged with No Phone")
    
    # Записуємо оновлений файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return changes_made

if __name__ == "__main__":
    changes = remove_phone_optin_ui()
    
    if changes:
        print("🎉 PHONE OPT-IN ВИДАЛЕНО З ФРОНТЕНД UI!")
        print("=" * 50)
        for change in changes:
            print(change)
        
        print("\n🎯 НОВА UI СТРУКТУРА:")
        print("✅ Тільки 2 сценарії:")
        print("  1. 💬 No Phone / Customer Reply")
        print("     • Звичайні ліди без номера")
        print("     • Phone Opt-In ліди (об'єднано!)")
        print("     • Customer replies без номера")
        
        print("\n  2. 📞 Real Phone / Phone Available") 
        print("     • Ліди з номером у тексті")
        print("     • Customer replies з номером")
        
        print("\n🗑️ ВИДАЛЕНО:")
        print("❌ Phone Opt-In tab")
        print("❌ phoneOptIn state")
        print("❌ Окремі Phone Opt-In налаштування")
        print("❌ Складна логіка вибору сценаріїв")
        
        print("\n✅ СПРОЩЕНО:")
        print("• Простіший UI з 2 tabs замість 3")
        print("• Менше плутанини для користувачів")
        print("• Уніфіковані налаштування для phone opt-in")
        
    else:
        print("❌ Не вдалося оновити фронтенд")
