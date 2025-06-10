# Fixing Virtual Environment Permission Issues

## The Problem

When trying to set up a new virtual environment using the command:
```
python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt && pip install -r tests/requirements-test.txt
```

You encounter a permission error:
```
Error: [Errno 13] Permission denied: 'D:\\Mygames\\HCshinobi\\venv\\Scripts\\python.exe'
```

This occurs when:
1. The `venv` directory already exists but has incorrect permissions
2. Another process might be locking the files in the `venv` directory
3. You don't have sufficient permissions to modify the files

## Our Solution

We created two scripts to fix this issue:

### 1. For PowerShell Users (`fix_venv.ps1`)

This script:
- Removes the existing virtual environment directory
- Creates a new clean virtual environment
- Activates the virtual environment
- Installs all required packages from both `requirements.txt` and `tests/requirements-test.txt`
- Installs the project in development mode

To use it:
```powershell
.\fix_venv.ps1
```

If you still encounter permission issues, try running PowerShell as administrator and then running the script.

### 2. For Command Prompt Users (`fix_venv.bat`)

This batch file performs the same actions as the PowerShell script but is designed for Command Prompt.

To use it:
```cmd
fix_venv.bat
```

If you still encounter permission issues, try running Command Prompt as administrator.

## What These Scripts Do

1. **Remove Existing Environment**: Safely removes the `venv` directory if it exists
2. **Create Fresh Environment**: Creates a new clean virtual environment
3. **Install Dependencies**: Installs all required packages for both development and testing
4. **Install in Development Mode**: Installs the HCShinobi package in development mode

## After Running the Fix

After successfully running either of these scripts, you can run the bot using:

```
python launch_bot.py
```

or

```
.\Start_Bot.bat
```

## Why This Works

The fix works by completely removing the problematic virtual environment and creating a fresh one with proper permissions. By using the script, you avoid the complex command chain that might fail if any step encounters an issue. 