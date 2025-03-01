"""
Script to create initial translation files for Scout.
"""

import os
import sys

def create_en_file():
    """Create English translation file."""
    content = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US" sourcelanguage="en_US">
<context>
    <name>MainWindow</name>
    <message>
        <source>Scout</source>
        <translation>Scout</translation>
    </message>
    <message>
        <source>File</source>
        <translation>File</translation>
    </message>
    <message>
        <source>Edit</source>
        <translation>Edit</translation>
    </message>
    <message>
        <source>View</source>
        <translation>View</translation>
    </message>
    <message>
        <source>Tools</source>
        <translation>Tools</translation>
    </message>
    <message>
        <source>Help</source>
        <translation>Help</translation>
    </message>
    <message>
        <source>Ready</source>
        <translation>Ready</translation>
    </message>
</context>
<context>
    <name>SettingsTab</name>
    <message>
        <source>Settings</source>
        <translation>Settings</translation>
    </message>
    <message>
        <source>Language</source>
        <translation>Language</translation>
    </message>
    <message>
        <source>Application Language:</source>
        <translation>Application Language:</translation>
    </message>
    <message>
        <source>System Default</source>
        <translation>System Default</translation>
    </message>
    <message>
        <source>English</source>
        <translation>English</translation>
    </message>
    <message>
        <source>German</source>
        <translation>German</translation>
    </message>
    <message>
        <source>Note: Some changes may require an application restart.</source>
        <translation>Note: Some changes may require an application restart.</translation>
    </message>
</context>
</TS>
"""
    with open('scout_en.ts', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Created scout_en.ts")

def create_de_file():
    """Create German translation file."""
    content = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en_US">
<context>
    <name>MainWindow</name>
    <message>
        <source>Scout</source>
        <translation>Scout</translation>
    </message>
    <message>
        <source>File</source>
        <translation>Datei</translation>
    </message>
    <message>
        <source>Edit</source>
        <translation>Bearbeiten</translation>
    </message>
    <message>
        <source>View</source>
        <translation>Ansicht</translation>
    </message>
    <message>
        <source>Tools</source>
        <translation>Werkzeuge</translation>
    </message>
    <message>
        <source>Help</source>
        <translation>Hilfe</translation>
    </message>
    <message>
        <source>Ready</source>
        <translation>Bereit</translation>
    </message>
</context>
<context>
    <name>SettingsTab</name>
    <message>
        <source>Settings</source>
        <translation>Einstellungen</translation>
    </message>
    <message>
        <source>Language</source>
        <translation>Sprache</translation>
    </message>
    <message>
        <source>Application Language:</source>
        <translation>Anwendungssprache:</translation>
    </message>
    <message>
        <source>System Default</source>
        <translation>Systemstandard</translation>
    </message>
    <message>
        <source>English</source>
        <translation>Englisch</translation>
    </message>
    <message>
        <source>German</source>
        <translation>Deutsch</translation>
    </message>
    <message>
        <source>Note: Some changes may require an application restart.</source>
        <translation>Hinweis: Einige Änderungen erfordern möglicherweise einen Neustart der Anwendung.</translation>
    </message>
</context>
</TS>
"""
    with open('scout_de.ts', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Created scout_de.ts")

if __name__ == "__main__":
    create_en_file()
    create_de_file()
    print("Translation files created successfully") 