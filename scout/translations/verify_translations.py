"""
Verify Translations

This script verifies the translation setup and ensures all files are correctly structured.
"""

import os
import sys
import logging
from pathlib import Path
import xml.etree.ElementTree as ET

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def verify_translation_file(ts_file: Path) -> bool:
    """
    Verify a .ts translation file.
    
    Args:
        ts_file: Path to the .ts file
        
    Returns:
        True if file is valid, False otherwise
    """
    if not ts_file.exists():
        logger.error(f"Translation file does not exist: {ts_file}")
        return False
        
    try:
        # Parse XML
        tree = ET.parse(ts_file)
        root = tree.getroot()
        
        # Check TS version
        if 'version' not in root.attrib:
            logger.error(f"Missing version attribute in {ts_file}")
            return False
            
        # Check language
        if 'language' not in root.attrib:
            logger.error(f"Missing language attribute in {ts_file}")
            return False
            
        # Count contexts and messages
        contexts = root.findall('context')
        context_count = len(contexts)
        
        message_count = 0
        translated_count = 0
        
        for context in contexts:
            name_elem = context.find('name')
            if name_elem is None:
                logger.warning(f"Context without name in {ts_file}")
                continue
                
            context_name = name_elem.text
            context_messages = context.findall('message')
            
            for message in context_messages:
                message_count += 1
                
                source = message.find('source')
                if source is None or not source.text:
                    logger.warning(f"Message without source text in context {context_name}")
                    continue
                    
                translation = message.find('translation')
                if translation is not None and translation.text:
                    translated_count += 1
        
        # Log statistics
        logger.info(f"File: {ts_file.name}")
        logger.info(f"  - Contexts: {context_count}")
        logger.info(f"  - Messages: {message_count}")
        logger.info(f"  - Translated: {translated_count} ({translated_count/message_count*100:.1f}%)")
        
        return True
    except Exception as e:
        logger.error(f"Error parsing {ts_file}: {str(e)}")
        return False

def verify_qm_file(qm_file: Path) -> bool:
    """
    Verify a .qm translation file.
    
    Args:
        qm_file: Path to the .qm file
        
    Returns:
        True if file exists and is not empty, False otherwise
    """
    if not qm_file.exists():
        logger.error(f"QM file does not exist: {qm_file}")
        return False
        
    if qm_file.stat().st_size == 0:
        logger.error(f"QM file is empty: {qm_file}")
        return False
        
    logger.info(f"QM file verified: {qm_file.name} ({qm_file.stat().st_size} bytes)")
    return True

def check_translation_pairs(ts_files: list[Path]) -> bool:
    """
    Check if each .ts file has a corresponding .qm file.
    
    Args:
        ts_files: List of .ts files
        
    Returns:
        True if all .ts files have corresponding .qm files, False otherwise
    """
    all_valid = True
    
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        
        if not qm_file.exists():
            logger.warning(f"Missing QM file for {ts_file}")
            all_valid = False
    
    return all_valid

def verify_all_translations():
    """Verify all translation files in the translations directory."""
    # Get translations directory
    script_dir = Path(__file__).parent
    ts_files = list(script_dir.glob("*.ts"))
    
    if not ts_files:
        logger.warning("No translation files found in the translations directory.")
        return
    
    logger.info(f"Found {len(ts_files)} translation files.")
    
    # Check each TS file
    valid_count = 0
    for ts_file in ts_files:
        if verify_translation_file(ts_file):
            valid_count += 1
    
    # Check QM files
    check_translation_pairs(ts_files)
    
    logger.info(f"Verified {valid_count} of {len(ts_files)} translation files successfully.")
    
    # Check for duplicate or incomplete entries
    check_for_issues(ts_files)

def check_for_issues(ts_files: list[Path]):
    """
    Check for common issues in translation files.
    
    Args:
        ts_files: List of translation files
    """
    all_messages = {}
    
    # First pass - collect all messages
    for ts_file in ts_files:
        try:
            tree = ET.parse(ts_file)
            root = tree.getroot()
            
            for context in root.findall('context'):
                name_elem = context.find('name')
                if name_elem is None:
                    continue
                    
                context_name = name_elem.text
                
                for message in context.findall('message'):
                    source = message.find('source')
                    if source is None or not source.text:
                        continue
                        
                    key = f"{context_name}:{source.text}"
                    
                    if key not in all_messages:
                        all_messages[key] = []
                    
                    translation_elem = message.find('translation')
                    translation_text = translation_elem.text if translation_elem is not None and translation_elem.text else None
                    
                    all_messages[key].append({
                        'file': ts_file.name,
                        'translation': translation_text
                    })
        except Exception as e:
            logger.error(f"Error checking for issues in {ts_file}: {str(e)}")
    
    # Second pass - check for issues
    for key, instances in all_messages.items():
        # Check for duplicates
        if len(instances) > len(ts_files):
            logger.warning(f"Duplicate entry '{key}' found in files:")
            for instance in instances:
                logger.warning(f"  - {instance['file']}")
        
        # Check for missing translations
        for instance in instances:
            if instance['translation'] is None:
                logger.warning(f"Missing translation for '{key}' in file {instance['file']}")

if __name__ == "__main__":
    verify_all_translations() 