#!/usr/bin/env python3
"""
Translation Checker

This script scans the codebase for potential translation and layout issues,
such as hardcoded strings, layout problems, and missing translations.
It generates a report to help developers address these issues.
"""

import os
import re
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from xml.etree import ElementTree as ET

# Import configuration
from scout.translations.config import (
    HARDCODED_STRING_PATTERNS,
    TR_PATTERN,
    LONG_TEXT_THRESHOLD,
    POTENTIAL_LAYOUT_ISSUE_PATTERN,
    EXCLUDED_DIRS,
    UI_FILE_EXTENSIONS,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class TranslationChecker:
    """
    Checks the codebase for translation and layout issues.
    
    This class scans Python and UI files for hardcoded strings, layout issues,
    and other potential problems related to internationalization.
    """
    
    def __init__(self, root_dir: Path):
        """
        Initialize the translation checker.
        
        Args:
            root_dir: Root directory of the codebase to check
        """
        self.root_dir = root_dir
        self.ui_files: List[Path] = []
        self.py_files: List[Path] = []
        self.ts_files: List[Path] = []
        self.hardcoded_strings: Dict[Path, List[Tuple[int, str]]] = {}
        self.missing_tr_calls: Dict[Path, List[Tuple[int, str]]] = {}
        self.layout_issues: Dict[Path, List[Tuple[int, str]]] = {}
        self.long_text_issues: Dict[Path, List[Tuple[int, str]]] = {}
        self.ts_contexts: Dict[str, Set[str]] = {}  # context -> set of source strings
    
    def find_files(self) -> None:
        """Find all relevant files in the codebase."""
        logger.info(f"Scanning directory: {self.root_dir}")
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()
                
                if file_ext == '.py':
                    self.py_files.append(file_path)
                elif file_ext == '.ui':
                    self.ui_files.append(file_path)
                elif file_ext == '.ts':
                    self.ts_files.append(file_path)
        
        logger.info(f"Found {len(self.py_files)} Python files")
        logger.info(f"Found {len(self.ui_files)} UI files")
        logger.info(f"Found {len(self.ts_files)} translation files")
    
    def parse_ts_files(self) -> None:
        """Parse translation files to extract contexts and source strings."""
        for ts_file in self.ts_files:
            try:
                tree = ET.parse(ts_file)
                root = tree.getroot()
                
                for context in root.findall(".//context"):
                    context_name = context.find("name").text if context.find("name") is not None else "unknown"
                    
                    if context_name not in self.ts_contexts:
                        self.ts_contexts[context_name] = set()
                    
                    for message in context.findall("message"):
                        source = message.find("source")
                        if source is not None and source.text:
                            self.ts_contexts[context_name].add(source.text)
            
            except Exception as e:
                logger.error(f"Error parsing {ts_file}: {str(e)}")
    
    def check_py_files(self) -> None:
        """Check Python files for translation and layout issues."""
        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                
                # Check for hardcoded strings
                file_hardcoded = []
                for i, line in enumerate(lines):
                    for pattern in HARDCODED_STRING_PATTERNS:
                        matches = pattern.findall(line)
                        if matches:
                            # Check if there's a tr call in the same line to avoid false positives
                            if not TR_PATTERN.search(line):
                                for match in matches:
                                    # Ignore empty strings and numeric-only strings
                                    if match and not match.isdigit() and len(match) > 1:
                                        file_hardcoded.append((i + 1, match))
                
                if file_hardcoded:
                    self.hardcoded_strings[file_path] = file_hardcoded
                
                # Check for layout issues (fixed sizes)
                file_layout_issues = []
                for i, line in enumerate(lines):
                    matches = POTENTIAL_LAYOUT_ISSUE_PATTERN.findall(line)
                    if matches:
                        file_layout_issues.append((i + 1, line.strip()))
                
                if file_layout_issues:
                    self.layout_issues[file_path] = file_layout_issues
                
                # Check for long text in tr calls
                file_long_text = []
                for i, line in enumerate(lines):
                    matches = TR_PATTERN.findall(line)
                    if matches:
                        for _, text in matches:
                            if len(text) > LONG_TEXT_THRESHOLD:
                                file_long_text.append((i + 1, text))
                
                if file_long_text:
                    self.long_text_issues[file_path] = file_long_text
            
            except Exception as e:
                logger.error(f"Error checking {file_path}: {str(e)}")
    
    def check_ui_files(self) -> None:
        """Check UI files for translation and layout issues."""
        for file_path in self.ui_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Simple check for hardcoded strings in UI files
                tree = ET.fromstring(content)
                
                file_hardcoded = []
                line_num = 1  # UI files don't have line numbers easily accessible
                
                # Find all string properties
                for string_prop in tree.findall(".//string"):
                    # Check if it has a translation context
                    if string_prop.get("notr") != "true" and not string_prop.get("comment"):
                        text = string_prop.text
                        if text and not text.isdigit() and len(text) > 1:
                            file_hardcoded.append((line_num, text))
                            line_num += 1
                
                if file_hardcoded:
                    self.hardcoded_strings[file_path] = file_hardcoded
                
                # Check for fixed width/height properties
                file_layout_issues = []
                line_num = 1
                
                for rect in tree.findall(".//rect"):
                    width = rect.get("width")
                    height = rect.get("height")
                    if width or height:
                        file_layout_issues.append((line_num, f"Fixed size: width={width}, height={height}"))
                        line_num += 1
                
                if file_layout_issues:
                    self.layout_issues[file_path] = file_layout_issues
            
            except Exception as e:
                logger.error(f"Error checking UI file {file_path}: {str(e)}")
    
    def check_missing_translations(self) -> None:
        """Check for strings that are marked for translation but missing in .ts files."""
        # Extract all tr calls from Python files
        all_tr_calls = set()
        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                matches = TR_PATTERN.findall(content)
                for _, text in matches:
                    all_tr_calls.add(text)
            
            except Exception as e:
                logger.error(f"Error extracting tr calls from {file_path}: {str(e)}")
        
        # Check if these strings are in the .ts files
        all_ts_strings = set()
        for context_strings in self.ts_contexts.values():
            all_ts_strings.update(context_strings)
        
        missing_translations = all_tr_calls - all_ts_strings
        
        if missing_translations:
            logger.warning(f"Found {len(missing_translations)} strings marked for translation but missing in .ts files")
            for text in sorted(missing_translations):
                logger.warning(f"  - {text}")
    
    def generate_report(self) -> None:
        """Generate a report of all issues found."""
        print("\n" + "=" * 80)
        print(" TRANSLATION AND LAYOUT ISSUES REPORT ")
        print("=" * 80 + "\n")
        
        # Report hardcoded strings
        if self.hardcoded_strings:
            print(f"\n[HARDCODED STRINGS] Found {sum(len(strings) for strings in self.hardcoded_strings.values())} hardcoded strings in {len(self.hardcoded_strings)} files")
            for file_path, strings in sorted(self.hardcoded_strings.items()):
                rel_path = file_path.relative_to(self.root_dir)
                print(f"\n  {rel_path}:")
                for line_num, text in strings:
                    print(f"    Line {line_num}: \"{text}\"")
        else:
            print("[HARDCODED STRINGS] No hardcoded strings found")
        
        # Report layout issues
        if self.layout_issues:
            print(f"\n[LAYOUT ISSUES] Found {sum(len(issues) for issues in self.layout_issues.values())} potential layout issues in {len(self.layout_issues)} files")
            for file_path, issues in sorted(self.layout_issues.items()):
                rel_path = file_path.relative_to(self.root_dir)
                print(f"\n  {rel_path}:")
                for line_num, text in issues:
                    print(f"    Line {line_num}: {text}")
        else:
            print("[LAYOUT ISSUES] No layout issues found")
        
        # Report long text issues
        if self.long_text_issues:
            print(f"\n[LONG TEXT] Found {sum(len(issues) for issues in self.long_text_issues.values())} long text strings in {len(self.long_text_issues)} files")
            for file_path, issues in sorted(self.long_text_issues.items()):
                rel_path = file_path.relative_to(self.root_dir)
                print(f"\n  {rel_path}:")
                for line_num, text in issues:
                    print(f"    Line {line_num}: \"{text}\"")
        else:
            print("[LONG TEXT] No long text issues found")
        
        # Summary
        print("\n" + "=" * 80)
        print(" SUMMARY ")
        print("=" * 80)
        print(f"Total files checked: {len(self.py_files) + len(self.ui_files)}")
        print(f"Total hardcoded strings: {sum(len(strings) for strings in self.hardcoded_strings.values())}")
        print(f"Total layout issues: {sum(len(issues) for issues in self.layout_issues.values())}")
        print(f"Total long text issues: {sum(len(issues) for issues in self.long_text_issues.values())}")
        print("=" * 80 + "\n")
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print("1. Replace hardcoded strings with tr() calls")
        print("2. Avoid fixed sizes and use layout helpers to handle different text lengths")
        print("3. Consider splitting long texts into smaller chunks")
        print("4. Run 'create_ts_files.py' to update translation files")
        print("5. Use the translator application to visually test layouts")
        print("6. Use the layout helper utilities for dynamic sizing based on language")
    
    def run(self) -> None:
        """Run all checks and generate a report."""
        self.find_files()
        self.parse_ts_files()
        self.check_py_files()
        self.check_ui_files()
        self.check_missing_translations()
        self.generate_report()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Check for translation and layout issues in the codebase")
    parser.add_argument("--dir", "-d", type=str, help="Root directory to scan", default=".")
    args = parser.parse_args()
    
    root_dir = Path(args.dir).resolve()
    checker = TranslationChecker(root_dir)
    checker.run()


if __name__ == "__main__":
    main() 