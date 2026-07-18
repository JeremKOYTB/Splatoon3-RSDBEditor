# Splatoon 3 RSDB Editor

A simple tool to edit and customize Splatoon 3 RSDB (Resource database) files for fun!

It allows you to modify weapon loadouts (Sub weapons, Special weapons, and Special points) using an intuitive interface, or dive deep into the raw BYML data.

<img width="3750" height="2142" alt="image" src="https://github.com/user-attachments/assets/4017141e-552a-4fbe-af7f-1274587b8769" />

---

## ⚠️ Critical Warning: Online Safety & Bannable Risks

**READ THIS CAREFULLY BEFORE USING:**

> [!CAUTION]
> * **Offline Use Only:** This tool, and all the files it generates, is strictly for offline use. Any modification to the game files is immediately detected by Nintendo's security systems if the console is connected to servers.
> * **Ban Risk:** Modifying game files will result in a permanent console and/or account ban from Nintendo services.
> * **User Responsibility:** By using this tool, you acknowledge that any resulting ban is entirely your own responsibility. Ensure your console remains offline when using modded files.

## About the Project

The **Splatoon 3 RSDB Editor** is a comprehensive GUI tool designed to manipulate the game's `.rstbl.byml.zs` database files. 
It simplifies editing weapon loadouts (`WeaponInfoMain`, `WeaponInfoSub`, `WeaponInfoSpecial`) and offers an Advanced Mode for raw data manipulation.

> **Note:** This project is intended for Windows 10 22H2/11. If there are any problems under Linux/macOS, I'm not aware of them.

> **Note 2:** Basic knowledge of Splatoon 3 data structures is recommended if you plan to use this script.

---

## Key Features

* **Dual Editing Modes:**

 **Easy Mode:** Quickly change Sub Weapons, Special Weapons, and Special Points via an easy-to-use dropdown interface.
(Note: Easy Mode will support other types of modifications beyond just Sub Weapons, Special Weapons, etc. Stay tuned!)

 **Expert Mode:** A comprehensive Tree-View editor to modify the raw BYML properties of the RSDB files.
 
---

* **Smart Filtering:** Hide Salmon Run (Coop), Story Mode/Side Order, or "NotFound" weapons to easily find what you are looking for.
* **Auto-Localization & Caching:** Automatically downloads and caches weapon icons and translated names (Supports multiple languages including US/EU English, French, Spanish, German, Italian, Dutch, and Japanese).
* **Integrated Updater:** Keep the tool up to date directly from the app.

---

## Prerequisites

1. **Python 3.11 or 3.12:** (Strictly required for compatibility with the BYML and Zstandard libraries).
2. **Game Data Files:** Valid Splatoon 3 RSDB files, specifically:
   * `WeaponInfoMain.Product.XXX.rstbl.byml.zs`
   * `WeaponInfoSub.Product.XXX.rstbl.byml.zs`
   * `WeaponInfoSpecial.Product.XXX.rstbl.byml.zs`

---

## Installation

1. Download the latest release from the **Releases** page.
2. Extract the contents to your preferred directory.
3. Execute **`Start.bat`**.
4. The script will automatically check your Python version, create an isolated virtual environment (`.venv`), and install all necessary dependencies.

---

## Usage

**0. Launching**

Run `Start.bat` to launch the editor. This script verifies updates, manages the cache, and ensures the environment is correctly configured.

**1. Preparation**

First, ensure you have the full game files extracted on your PC. You do not need a powerful computer, but it must be running at least Windows 10.

 * I recommend using **Ryujinx** to extract the files (you do not need to launch the game).
 * Right-click the game in Ryujinx and extract the **RomFS** folder.

**2. Opening the editor**

 * Launch the **RSDB Editor**.
 * Click **Open RSDB Folder**.
 * Navigate to your extracted romfs folder, go into the **RSDB** folder, and select it.
 * The tool will automatically download missing weapon icons and build the cache. Once loaded, you can select the weapon you want to modify from the left panel.

**3. Modifying weapons**
 * **Easy Mode:** Select a weapon, then simply choose a new Sub Weapon or Special Weapon from the dropdown menus. You can also edit the "Special Points" required for the special.
 * **Expert Mode:** Click the "Switch to Expert Mode" button to view the raw data structure. You can edit booleans, integers, floats, and strings directly.

**4. Saving and applying changes**
 * Once you are finished, click **Save Changes** and choose where to save your modified `.rstbl.byml.zs` files. You can then close the script.
* To apply these changes in-game, place the new files exactly in this path on your SD card (replace `XXX` with your game version, e.g., `b20`):
  `sd:/atmosphere/contents/0100C2500FC20000/RomFS/RSDB/`

> ⚠️ Warning regarding game updates:
> When the game updates, it is highly likely that the RSDB files are also updated. Your previous modifications will then stop working. 

To make your mod compatible again after an update, you have two options:

1. Remake your modifications on the new file (Highly Recommended):
   It is strongly advised to recreate your mod based on the RSDB file from the new version. Nintendo often adds new content (like new weapons) during updates, and using the old file could cause bugs or missing content.

2. Rename your current file (Quick fix):
   You can simply rename your current file to match the new version. 
   * Example: Rename `WeaponInfoMain.Product.XXX.rstbl.byml.zs` to `WeaponInfoMain.Product.YYY.rstbl.byml.zs`
   * XXX = Your current version
   * YYY = The new game version

---

If you followed these steps correctly, your modified loadouts will appear in the game. Feel free to ask if you have any questions, run into any issues, or are unsure about any part of this process! :)

---

## Transparency & Contributions

* **AI Assistance:** This project was developed with the assistance of **Gemini** to translate concepts into functional Python code (but ideas/features come from me).
* **Open Source:** This project is collaborative. Contributions are encouraged to improve robustness and maintainability.
* Use the **Issue** tab [HERE](https://github.com/JeremKOYTB/Splatoon3-RSDBEditor/issues) to report bugs.
* Submit a **Pull Request** for fixes or feature enhancements.

---

## Credits

* Thanks to [Leanny](https://leanny.github.io/splat3/) for the localization data, image hosting, and file structure research.
* Thanks to the Splatoon modding/[Switch-Toolbox](https://github.com/KillzXGaming/Switch-Toolbox) community for their ongoing research into Nintendo file formats.

---

*Developed by JérémKO.*

*Licensed under the MIT License.*
