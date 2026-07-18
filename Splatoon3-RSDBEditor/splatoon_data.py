import os
import json
import requests
import re
from datetime import datetime
import byml

from utils import log, CACHE_DIR
from translations import t

class SplatoonDataManager:
    def __init__(self):
        self.localization_data = {}

    def is_file_outdated(self, url, local_path):
        try:
            response = requests.head(url, timeout=5)
            remote_last_modified = response.headers.get("Last-Modified")
            if not remote_last_modified: return True
            remote_time = datetime.strptime(remote_last_modified, "%a, %d %b %Y %H:%M:%S %Z").timestamp()
            return remote_time > os.path.getmtime(local_path)
        except Exception as e:
            log(f"[NET] Cannot check headers for '{url}': {e}")
            return False

    def fetch_leanny_localization(self, lang_code):
        log(f"[DB] Fetching language file: {lang_code}.json")
        url = f"https://leanny.github.io/splat3/data/language/{lang_code}.json"
        local_path = os.path.join(CACHE_DIR, f"{lang_code}.json")
        
        needs_dl = True
        if os.path.exists(local_path):
            if not self.is_file_outdated(url, local_path):
                needs_dl = False
                try:
                    with open(local_path, "r", encoding="utf-8") as f:
                        self.localization_data = json.load(f)
                    log(f"[DB] DB {lang_code} loaded from local cache.")
                except Exception as e:
                    log(f"[DB] Cache read error ({e}), forcing redownload.")
                    needs_dl = True

        if needs_dl:
            log(f"[DB] Downloading {lang_code}.json from Github Pages...")
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                self.localization_data = resp.json()
                log(f"[DB] DB {lang_code} downloaded and secured in cache.")
            except Exception as e:
                log(f"[DB] Network failure downloading language: {e}")

    def _find_json_value(self, key, default):
        for category, items in self.localization_data.items():
            if isinstance(items, dict) and key in items:
                return items[key]
        return default

    def guess_image_and_name(self, internal_name, verbose=False):
        if not internal_name: return "Unknown", "Dummy.png", False, ""
        
        if internal_name in ["WeaponFree", "Free"]: return t("name_unarmed"), "Win_Tricol.png", True, "Free"
        if internal_name in ["WeaponSpIkuraShoot", "SpIkuraShoot"]: return "Smallfry", "SakelienSmall.png", True, "SpIkuraShoot"
        
        if "SalmonBuddy" in internal_name: return "SalmonBuddy", "Wsb_SalmonBuddy00.png", True, "SalmonBuddy"
        if "Drone" in internal_name: return "SpDroneBuddy", "Wsp_SpDroneBuddySdodr00.png", True, "SpDroneBuddy"
        
        clean = internal_name.replace("Weapon_", "") 
        
        if "Shooter_MissionLv" in clean or "Shooter_Normal_H" in clean:
            img = "Path_Wst_Shooter_Normal_H.png"
            for suffix in ["_Coop", "Coop", "_Mission", "Mission", "_Msn", "Msn", "_Hero", "Hero", "_Rival", "Rival", "_Sdodr", "Sdodr", "ForEventMatch"]:
                clean = clean.replace(suffix, "")
            clean = re.sub(r'Lv\d+', '', clean).strip('_')
            return clean, img, True, clean
        
        sdodr_overrides = {
            "Brush_Sdodr": "Wst_Brush_Normal_O.png",
            "Spinner_Sdodr": "Wst_Spinner_Standard_O.png",
            "Slosher_Sdodr": "Wst_Slosher_Strong_O.png",
            "Shooter_ExtraOne_Sdodr": "Wst_Shooter_Normal_O.png",
            "Shooter_ExtraTwo_Sdodr": "Wst_Shooter_Normal_Oct.png",
            "Charger_ExtraOne_Sdodr": "Wst_Charger_Normal_O.png",
            "Blaster_Sdodr": "Wst_Blaster_Middle_O.png",
            "Roller_Sdodr": "Wst_Roller_Normal_O.png",
            "Maneuver_Sdodr": "Wst_Maneuver_Normal_O.png",
            "Shelter_Sdodr": "Wst_Shelter_Normal_O.png",
            "Saber_Sdodr": "Wst_Saber_Normal_O.png",
            "Stringer_Sdodr": "Wst_Stringer_Normal_O.png"
        }
        
        if clean in sdodr_overrides:
            img = sdodr_overrides[clean]
            for suffix in ["_Coop", "Coop", "_Mission", "Mission", "_Msn", "Msn", "_Hero", "Hero", "_Rival", "Rival", "_Sdodr", "Sdodr", "ForEventMatch"]:
                clean = clean.replace(suffix, "")
            clean = re.sub(r'Lv\d+', '', clean).strip('_')
            return clean, img, True, clean
        
        for suffix in ["_Coop", "Coop", "_Mission", "Mission", "_Msn", "Msn", "_Hero", "Hero", "_Rival", "Rival", "_Sdodr", "Sdodr", "ForEventMatch"]:
            clean = clean.replace(suffix, "")
        clean = re.sub(r'Lv\d+', '', clean).strip('_')
        
        if clean.startswith("Bomb_") or clean in ["PointSensor", "PoisonMist", "LineMarker", "Sprinkler", "Shield", "Trap", "Beacon"]:
            img_clean = "Bomb_Splash" if "Bomb_Splash_Big" in internal_name else clean
            return clean, f"Wsb_{img_clean}00.png", True, clean
            
        if clean.startswith("Sp") and not clean.startswith("Spinner"):
            base_sp = clean.split('_')[0]
            if base_sp in ["SpGachihoko", "SpGachihokoForEventMatch"]: return clean, "Wsp_Shachihoko.png", True, clean
            return clean, f"Wsp_{base_sp}00.png", True, clean
                
        parts = clean.split('_')
        weapon_class = parts[0]
        
        default_type = "Normal"
        if weapon_class == "Blaster": default_type = "Middle"
        elif weapon_class == "Spinner": default_type = "Standard"
        elif weapon_class == "Slosher": default_type = "Strong"
        
        weapon_type = default_type
        variant = "00"
        
        if len(parts) == 2:
            if parts[1].isdigit() or parts[1] in ["O", "Oct"]:
                variant = parts[1]
            else:
                weapon_type = parts[1]
        elif len(parts) >= 3:
            weapon_type = parts[1]
            if parts[2].isdigit() or parts[2] in ["O", "Oct"]:
                variant = parts[2]
                
        if "Sdodr" in internal_name:
            variant = "O"
            
        if weapon_type == "Bear":
            img = f"Path_Wst_{weapon_class}_Bear.png"
        elif weapon_class == "Blaster" and weapon_type == "ExtraOne":
            img = "Wst_Blaster_Short_O.png"
        else:
            img = f"Wst_{weapon_class}_{weapon_type}_{variant}.png"
            
        return clean, img, True, clean

    def get_exact_translation(self, internal_name, json_key, return_is_hardcoded=False):
        if not internal_name: 
            return ("Unknown", False) if return_is_hardcoded else "Unknown"
        
        custom_hardcoded = {
            "SplPlayer": "Player",
            "WeaponFree": t("name_unarmed"),
            "Free": t("name_unarmed"),
            "SpIkuraShoot": "Smallfry",
            "SalmonBuddy": "Smallfry"
        }
        
        for key, val in custom_hardcoded.items():
            if key in internal_name:
                return (val, True) if return_is_hardcoded else val

        clean_name = internal_name.replace("Weapon_", "")
        
        vanilla_name = clean_name
        for suffix in ["_Coop", "Coop", "_Mission", "Mission", "_Msn", "Msn", "_Hero", "Hero", "_Rival", "Rival", "_Sdodr", "Sdodr", "ForEventMatch"]:
            vanilla_name = vanilla_name.replace(suffix, "")
        vanilla_name = re.sub(r'Lv\d+', '', vanilla_name).strip('_')

        if "Bomb_Splash_Big" in vanilla_name:
            vanilla_name = "Bomb_Splash"

        base_keys = [internal_name, clean_name, json_key, vanilla_name]
        
        if "Bomb_" in json_key:
            base_keys.append(json_key.replace("Bomb_", "Bomb").rstrip("0123456789_"))
        if "Bomb_" in vanilla_name:
            base_keys.append(vanilla_name.replace("Bomb_", "Bomb").rstrip("0123456789_"))
            
        categories = [
            "CommonMsg/Weapon/WeaponName_Main",
            "CommonMsg/Weapon/WeaponName_Sub",
            "CommonMsg/Weapon/WeaponName_Special"
        ]
        
        target_variant = ""
        match = re.search(r'_(\d{2})$', clean_name)
        if match:
            target_variant = match.group(1)
        elif "_O" in clean_name or "_Oct" in clean_name or "Sdodr" in clean_name:
            target_variant = "" 
            
        found_name = None
        for cat in categories:
            if cat in self.localization_data:
                dict_cat = self.localization_data[cat]
                
                for bk in base_keys:
                    exact_key = f"{bk.rstrip('0123456789_')}_{target_variant}" if target_variant else bk
                    
                    if exact_key in dict_cat:
                        val = dict_cat[exact_key].strip()
                        if val not in ["", "-"]:
                            found_name = val
                            break
                            
                    if bk in dict_cat:
                        val = dict_cat[bk].strip()
                        if val not in ["", "-"]:
                            found_name = val
                            break
            if found_name: break
                
        if not found_name:
            found_name = internal_name

        suffix_tag = ""
        if "Coop" in internal_name:
            tag = self._find_json_value("Coop", t("tag_coop"))
            suffix_tag = f" - {tag}"
        elif "ForEventMatch" in internal_name:
            tag = self._find_json_value("League", "Match Challenge")
            suffix_tag = f" - {tag}"
        elif "Sdodr" in internal_name:
            tag = self._find_json_value("Category_SideOrder_00", "Side Order")
            suffix_tag = f" - {tag}"
        elif any(m in internal_name for m in ["Mission", "Rival", "Hero", "_Msn", "Lv"]) or "SalmonBuddy" in internal_name or "Drone" in internal_name or "IkuraShoot" in internal_name:
            tag = self._find_json_value("ModeMission", t("tag_hero"))
            lv_match = re.search(r'Lv(\d+)', internal_name)
            if lv_match:
                tag += f" Lv{lv_match.group(1)}"
            suffix_tag = f" - {tag}"
            
        final_name = found_name + suffix_tag
        
        return (final_name, False) if return_is_hardcoded else final_name