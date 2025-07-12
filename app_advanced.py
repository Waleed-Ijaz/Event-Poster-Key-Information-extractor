import gradio as gr
import string
from collections import Counter
import re
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import tempfile
from PIL import Image
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# Initialize the OCR model
model = ocr_predictor(pretrained=True)

def clean_text(text):
    """Clean and normalize extracted text"""
    text = text.strip()
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text

import re
import string
from collections import Counter

def calculate_text_prominence(line, all_lines):
    """Calculate how prominent a line is based on various factors"""
    score = 0
    
    # Length factor (moderate length is good for titles)
    length = len(line.strip())
    if 10 <= length <= 80:
        score += 3
    elif 5 <= length <= 100:
        score += 2
    elif length > 100:
        score -= 2  # Too long, probably description
    
    # Position factor (earlier lines more likely to be titles)
    position = all_lines.index(line) + 1
    total_lines = len(all_lines)
    if position <= 3:
        score += 4
    elif position <= 5:
        score += 3
    elif position <= total_lines * 0.3:
        score += 2
    
    # Capitalization patterns
    words = line.strip().split()
    if len(words) > 0:
        # Title Case (Each Word Capitalized)
        title_case_count = sum(1 for word in words if word and word[0].isupper())
        if title_case_count == len(words) and len(words) > 1:
            score += 4
        elif title_case_count >= len(words) * 0.7:
            score += 3
        
        # ALL CAPS (common for event titles)
        if line.strip().isupper() and 3 <= len(words) <= 8:
            score += 3
        elif line.strip().isupper() and len(words) > 8:
            score -= 1  # Too many words in caps, might be description
    
    # Punctuation patterns
    if line.count('.') <= 1 and line.count(',') <= 2:
        score += 1
    if line.endswith(('!', '?')):
        score += 1
    if line.count(':') > 1 or line.count(';') > 0:
        score -= 2
    
    # Common event title indicators
    event_keywords = [
        'conference', 'summit', 'workshop', 'seminar', 'symposium', 'expo',
        'festival', 'concert', 'show', 'exhibition', 'fair', 'competition',
        'championship', 'tournament', 'meetup', 'gathering', 'celebration',
        'launch', 'presentation', 'webinar', 'bootcamp', 'hackathon',
        'convention', 'forum', 'congress', 'colloquium', 'masterclass'
    ]
    
    line_lower = line.lower()
    for keyword in event_keywords:
        if keyword in line_lower:
            score += 2
            break
    
    # Year patterns (events often have years in titles)
    if re.search(r'\b20\d{2}\b', line):
        score += 1
    
    # Edition/version patterns
    if re.search(r'\b(?:\d+(?:st|nd|rd|th)|first|second|third|annual)\b', line.lower()):
        score += 2
    
    return score

def is_likely_metadata(line):
    """Check if a line is likely to be metadata rather than event title"""
    line_lower = line.lower().strip()
    
    # Common metadata patterns
    metadata_patterns = [
        r'^\s*date\s*:',
        r'^\s*time\s*:',
        r'^\s*venue\s*:',
        r'^\s*location\s*:',
        r'^\s*contact\s*:',
        r'^\s*phone\s*:',
        r'^\s*email\s*:',
        r'^\s*price\s*:',
        r'^\s*fee\s*:',
        r'^\s*register\s*:',
        r'^\s*organised by',
        r'^\s*organized by',
        r'^\s*sponsored by',
        r'^\s*presented by',
        r'^\s*powered by',
        r'^\s*in association with',
        r'^\s*supported by',
        r'www\.',
        r'http[s]?://',
        r'@\w+',  # Social media handles
        r'^\s*follow us',
        r'^\s*visit us',
        r'^\s*call us',
        r'^\s*whatsapp',
        r'^\s*telegram',
        r'^\s*facebook',
        r'^\s*instagram',
        r'^\s*twitter',
        r'^\s*linkedin',
        r'admission',
        r'registration',
        r'certificate',
        r'refreshments',
        r'lunch',
        r'dinner',
        r'breakfast',
    ]
    
    for pattern in metadata_patterns:
        if re.search(pattern, line_lower):
            return True
    
    # Check for email patterns
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line):
        return True
    
    # Check for phone number patterns
    if re.search(r'(?:\+?\d[\d\s\-().]{7,}|\d{10,})', line):
        return True
    
    # Check for address-like patterns
    if re.search(r'\b(?:street|road|avenue|lane|drive|plaza|building|floor)\b', line_lower):
        return True
    
    # Check for very generic phrases
    generic_phrases = [
        'welcome', 'join us', 'dont miss', "don't miss", 'limited seats',
        'hurry up', 'book now', 'register now', 'apply now', 'click here',
        'for more information', 'terms and conditions', 'terms & conditions'
    ]
    
    for phrase in generic_phrases:
        if phrase in line_lower:
            return True
    
    return False

def extract_event_name(text):
    """
    Advanced event name extraction using multiple strategies and scoring
    """
    if not text or not text.strip():
        return "Not found"
    
    # Clean and split text into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return "Not found"
    
    # Remove obvious metadata lines
    filtered_lines = [line for line in lines if not is_likely_metadata(line)]
    
    if not filtered_lines:
        # Fallback to original lines if all were filtered
        filtered_lines = lines
    
    # Strategy 1: Look for explicit event name patterns
    explicit_patterns = [
        # "Event Name: XYZ" or "Title: XYZ"
        r'(?i)(?:event\s*name|title|event\s*title|name\s*of\s*event)\s*[:\-–=]\s*(.+?)(?:\n|$)',
        
        # "Presenting XYZ" or "Announces XYZ"
        r'(?i)(?:presenting|announces?|invites?\s+you\s+to|proudly\s+presents?)\s+(.+?)(?:\s+(?:on|at|in)\s+\d|\n|$)',
        
        # "Join us for XYZ" or "Welcome to XYZ"
        r'(?i)(?:join\s+us\s+for|welcome\s+to|attend)\s+(.+?)(?:\s+(?:on|at|in)\s+\d|\n|$)',
        
        # "XYZ Conference/Workshop/etc."
        r'(?i)(.+?(?:conference|workshop|seminar|symposium|summit|expo|festival|concert|show|exhibition|fair|competition|championship|tournament|meetup|gathering|celebration|launch|presentation|webinar|bootcamp|hackathon|convention|forum|congress|colloquium|masterclass)(?:\s+20\d{2})?)',
        
        # "Annual/1st/2nd XYZ"
        r'(?i)((?:annual|\d+(?:st|nd|rd|th)|first|second|third)\s+.+?)(?:\s+(?:on|at|in)\s+\d|\n|$)',
        
        # "XYZ 2024/2025" (event with year)
        r'(?i)(.+?\s+20\d{2})(?:\s|$)',
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            # Clean up the candidate
            candidate = re.sub(r'\s+', ' ', candidate)
            candidate = candidate.strip('.,;:!?-–')
            
            if 5 <= len(candidate) <= 100 and not is_likely_metadata(candidate):
                return candidate
    
    # Strategy 2: Score-based line analysis
    line_scores = []
    for line in filtered_lines[:15]:  # Focus on first 15 lines
        if len(line.strip()) < 3:  # Skip very short lines
            continue
            
        score = calculate_text_prominence(line, filtered_lines)
        line_scores.append((line, score))
    
    # Sort by score (highest first)
    line_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Strategy 3: Look for title-like formatting patterns
    for line, score in line_scores:
        line_clean = line.strip()
        
        # Skip if it looks like metadata
        if is_likely_metadata(line_clean):
            continue
        
        # Check for good title characteristics
        words = line_clean.split()
        
        # Good length for titles
        if not (2 <= len(words) <= 12):
            continue
        
        # Check for title case or appropriate capitalization
        if (line_clean.istitle() or 
            line_clean.isupper() or 
            sum(1 for word in words if word and word[0].isupper()) >= len(words) * 0.6):
            
            # Additional validation
            if not re.search(r'^\d+\s*[.:]', line_clean):  # Not a numbered item
                return line_clean
    
    # Strategy 4: Pattern-based extraction from high-scoring lines
    for line, score in line_scores[:5]:  # Top 5 lines
        line_clean = line.strip()
        
        # Try to extract the main part of the line
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            r'(?i)^(?:the\s+)?(?:annual\s+)?\d+(?:st|nd|rd|th)\s+',
            r'(?i)^(?:welcome\s+to\s+)?(?:the\s+)?',
            r'(?i)^(?:join\s+us\s+for\s+)?(?:the\s+)?',
            r'(?i)^(?:attend\s+)?(?:the\s+)?',
        ]
        
        cleaned_line = line_clean
        for prefix_pattern in prefixes_to_remove:
            cleaned_line = re.sub(prefix_pattern, '', cleaned_line).strip()
        
        # Remove trailing year if present
        cleaned_line = re.sub(r'\s+20\d{2}$', '', cleaned_line).strip()
        
        if 5 <= len(cleaned_line) <= 80 and not is_likely_metadata(cleaned_line):
            return cleaned_line
    
    # Strategy 5: Fallback to first substantial non-metadata line
    for line in filtered_lines[:10]:
        line_clean = line.strip()
        if (5 <= len(line_clean) <= 100 and 
            not is_likely_metadata(line_clean) and
            not re.match(r'^\d+[.:]', line_clean)):  # Not numbered
            return line_clean
    
    # Strategy 6: Last resort - look for any line with event keywords
    event_keywords = [
        'conference', 'summit', 'workshop', 'seminar', 'symposium', 'expo',
        'festival', 'concert', 'show', 'exhibition', 'fair', 'competition',
        'championship', 'tournament', 'meetup', 'gathering', 'celebration',
        'launch', 'presentation', 'webinar', 'bootcamp', 'hackathon'
    ]
    
    for line in lines:
        line_lower = line.lower()
        for keyword in event_keywords:
            if keyword in line_lower and 10 <= len(line) <= 100:
                return line.strip()
    
    # Final fallback
    if filtered_lines:
        first_line = filtered_lines[0].strip()
        if 3 <= len(first_line) <= 100:
            return first_line
    
    return "Not found"


def clean_and_normalize_date(date_str, month_mapping, day_mapping):
    """Clean and normalize extracted date string"""
    if not date_str:
        return "Not found"
    
    # Convert to lowercase for processing
    date_lower = date_str.lower()
    
    # Replace common misspellings and normalize
    for abbrev, full in month_mapping.items():
        if abbrev in date_lower:
            date_str = re.sub(r'\b' + re.escape(abbrev) + r'\b', full, date_str, flags=re.IGNORECASE)
            break
    
    # Replace day abbreviations
    for abbrev, full in day_mapping.items():
        if abbrev in date_lower:
            date_str = re.sub(r'\b' + re.escape(abbrev) + r'\b', full, date_str, flags=re.IGNORECASE)
            break
    
    # Clean up spacing and punctuation
    date_str = re.sub(r'\s+', ' ', date_str)
    date_str = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', date_str)  # Add space between letters and numbers
    date_str = date_str.replace('  ', ' ').strip()
    
    return date_str

def extract_partial_dates(text, month_mapping, day_mapping):
    """Extract partial date information when full patterns don't match"""
    
    # Look for any month names
    month_pattern = r'(?i)\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\b'
    month_matches = re.findall(month_pattern, text)
    
    # Look for years
    year_pattern = r'\b(20\d{2})\b'
    year_matches = re.findall(year_pattern, text)
    
    # Look for day numbers (1-31)
    day_pattern = r'\b(\d{1,2})(?:st|nd|rd|th)?\b'
    day_matches = re.findall(day_pattern, text)
    
    # Look for day names
    day_name_pattern = r'(?i)\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b'
    day_name_matches = re.findall(day_name_pattern, text)
    
    # Try to construct a date from available components
    result_parts = []
    
    if day_name_matches:
        day_name = day_name_matches[0].lower()
        if day_name in day_mapping:
            result_parts.append(day_mapping[day_name])
    
    if month_matches:
        month = month_matches[0].lower()
        if month in month_mapping:
            result_parts.append(month_mapping[month])
    
    # Filter day numbers to reasonable date range (1-31)
    valid_days = [d for d in day_matches if 1 <= int(d) <= 31]
    if valid_days:
        result_parts.append(valid_days[0])
    
    if year_matches:
        result_parts.append(year_matches[0])
    
    if result_parts:
        return ' '.join(result_parts)
    
    return "Not found"

def extract_date(text):
    """Extract date information using comprehensive regex patterns"""
    
    # Month name mappings for normalization
    month_mapping = {
        'jan': 'January', 'january': 'January',
        'feb': 'February', 'february': 'February', 'feburary': 'February',  # Common misspelling
        'mar': 'March', 'march': 'March',
        'apr': 'April', 'april': 'April',
        'may': 'May',
        'jun': 'June', 'june': 'June',
        'jul': 'July', 'july': 'July',
        'aug': 'August', 'august': 'August',
        'sep': 'September', 'september': 'September', 'sept': 'September',
        'oct': 'October', 'october': 'October',
        'nov': 'November', 'november': 'November',
        'dec': 'December', 'december': 'December'
    }
    
    # Day name mappings
    day_mapping = {
        'mon': 'Monday', 'monday': 'Monday',
        'tue': 'Tuesday', 'tuesday': 'Tuesday', 'tues': 'Tuesday',
        'wed': 'Wednesday', 'wednesday': 'Wednesday',
        'thu': 'Thursday', 'thursday': 'Thursday', 'thur': 'Thursday', 'thurs': 'Thursday',
        'fri': 'Friday', 'friday': 'Friday',
        'sat': 'Saturday', 'saturday': 'Saturday',
        'sun': 'Sunday', 'sunday': 'Sunday'
    }
    
    # Comprehensive date patterns (ordered by specificity)
    date_patterns = [
        # Full date ranges: "January 18-19, 2025" or "18-19 January 2025"
        r'(?i)(?:date\s*:?\s*)?(\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–]\s*\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})\b',
        
        # Date ranges with month at end: "18-19 January 2025"
        r'(?i)(?:date\s*:?\s*)?(\b\d{1,2}(?:st|nd|rd|th)?\s*[-–]\s*\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{4})\b',
        
        # Day name with date: "Saturday May 20th" or "SAT MAY20TH"
        r'(?i)(?:date\s*:?\s*)?(\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\s*\.?\s*(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s*\.?\s*\d{1,2}(?:st|nd|rd|th)?)\b',
        
        # Day name with numeric date: "THURSDAY 2/20"
        r'(?i)(?:date\s*:?\s*)?(\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\s*\.?\s*\d{1,2}\s*[/\-]\s*\d{1,2})\b',
        
        # Standard formats with ordinals: "28th February 2025"
        r'(?i)(?:date\s*:?\s*)?(\b\d{1,2}(?:st|nd|rd|th)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{4})\b',
        
        # Month Day, Year: "February 22-23, 2025"
        r'(?i)(?:date\s*:?\s*)?(\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–]?\s*\d{0,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})\b',
        
        # DD Month YYYY
        r'(?i)(?:date\s*:?\s*)?(\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\.?\s+\d{4})\b',
        
        # Numeric formats: DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY
        r'(?i)(?:date\s*:?\s*)?(\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b',
        
        # Year only in context: "2025"
        r'(?i)(?:date\s*:?\s*)?(\b(?:20)\d{2})\b',
        
        # Month and day without year: "May 20th", "20th May"
        r'(?i)(?:date\s*:?\s*)?(\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{1,2}(?:st|nd|rd|th)?)\b',
        r'(?i)(?:date\s*:?\s*)?(\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary))\b',
        
        # Just month and year: "February 2025"
        r'(?i)(?:date\s*:?\s*)?(\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|feburary)\s+\d{4})\b',
    ]
    
    # Try each pattern
    for pattern in date_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            date_str = match.group(1).strip()
            
            # Clean and normalize the extracted date
            date_str = clean_and_normalize_date(date_str, month_mapping, day_mapping)
            
            if date_str and date_str != "Not found":
                return date_str
    
    # If no pattern matches, look for isolated date components
    return extract_partial_dates(text, month_mapping, day_mapping)

def post_process_time(time_str):
    """Post-process extracted time string to clean and normalize it"""
    if not time_str:
        return "Not found"
    
    # Remove extra spaces
    time_str = re.sub(r'\s+', ' ', time_str).strip()
    
    # Normalize AM/PM formatting
    time_str = re.sub(r'(?i)\b([ap])\.?m\.?\b', lambda m: m.group(1).upper() + 'M', time_str)
    
    # Fix common OCR errors in time format
    time_str = re.sub(r'(?i)([0-9])[oO]([0-9])', r'\1:\2', time_str)  # "1O:00" -> "1:00"
    time_str = re.sub(r'\.(\d{2}\s*(?:AM|PM))', r':\1', time_str)  # "10.00 AM" -> "10:00 AM"
    
    # Add leading zero for single digit hours in 24-hour format
    if re.match(r'^\d:\d{2}$', time_str):
        time_str = '0' + time_str
    
    # Handle ranges and normalize separators
    time_str = re.sub(r'\s*[-–=]\s*', ' - ', time_str)
    
    # Validate that we have a reasonable time format
    if re.search(r'\d', time_str):  # At least contains a digit
        return time_str
    
    return "Not found"

def extract_time(text):
    """Extract time information using comprehensive regex patterns - IMPROVED VERSION"""
    
    # Preprocess text to handle OCR artifacts and normalize formatting
    def preprocess_time_text(text):
        # Replace common OCR misreadings
        text = re.sub(r'(?i)\b0(\d)\b', r'\1', text)  # "01.00" -> "1.00"
        text = re.sub(r'(?i)(\d)[oO](\d)', r'\1:\2', text)  # "1O:00" -> "1:00"
        text = re.sub(r'(?i)\.(?=\d{2}\s*(?:AM|PM|am|pm))', ':', text)  # "10.00 AM" -> "10:00 AM"
        text = re.sub(r'(?i)(\d)\s*[.,]\s*(\d{2})', r'\1:\2', text)  # "10.00" or "10, 00" -> "10:00"
        
        # Handle spacing issues around AM/PM
        text = re.sub(r'(?i)(\d)\s*(AM|PM)', r'\1 \2', text)  # "1PM" -> "1 PM"
        text = re.sub(r'(?i)(\d)\s*([AP])\s*[.,]?\s*M', r'\1 \2M', text)  # "1 P M" -> "1 PM"
        
        # Normalize dashes and time separators
        text = re.sub(r'[-–—−]+', '-', text)  # Normalize various dash types
        text = re.sub(r'\s*[-–—−]\s*', ' - ', text)  # Normalize spacing around dashes
        text = re.sub(r'\s*=\s*', ' - ', text)  # "10.00 AM = 01.00 PM" -> "10.00 AM - 01.00 PM"
        text = re.sub(r'\s*to\s*', ' - ', text, flags=re.IGNORECASE)  # "to" -> "-"
        
        return text
    
    # Preprocess the text
    processed_text = preprocess_time_text(text)
    
    # Comprehensive time patterns (ordered by complexity and specificity)
    time_patterns = [
        # Complex time ranges with various separators
        # "10:00 AM - 1:00 PM", "10.00 AM = 01.00 PM", "9AM-4PM"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)\s*[-–=]\s*\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.))',
        
        # Time ranges without AM/PM on first time: "10:00 - 1:00 PM"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}(?:[:.]\d{2})?\s*[-–=]\s*\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.))',
        
        # Single time with AM/PM: "1PM", "10:00 AM", "10.00 AM"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.))',
        
        # Time ranges in 24-hour format: "10:00 - 13:00", "10.00-13.00"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}[:.]\d{2}\s*[-–=]\s*\d{1,2}[:.]\d{2})',
        
        # Simple time ranges: "1-2PM", "9AM-4PM"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}\s*(?:AM|PM|am|pm)?\s*[-–=]\s*\d{1,2}\s*(?:AM|PM|am|pm))',
        
        # Time with context words: "from 10AM to 2PM", "between 1PM and 3PM"
        r'(?i)(?:from|between)\s+(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)?\s*(?:to|and|-)\s*\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm))',
        
        # Hours only with AM/PM: "1 PM", "10AM"
        r'(?i)(?:time\s*:?\s*)?(\d{1,2}\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.))',
        
        # 24-hour format: "13:00", "10.30"
        r'(?i)(?:time\s*:?\s*)?((?:0?[0-9]|1[0-9]|2[0-3])[:.]\d{2})',
        
        # Partial times that might be cut off: just hours
        r'(?i)(?:time\s*:?\s*)?(\d{1,2})(?=\s*(?:o\'clock|oclock|hours?))',
    ]
    
    # Try each pattern and return the first match
    for pattern in time_patterns:
        matches = re.finditer(pattern, processed_text)
        for match in matches:
            time_str = match.group(1).strip()
            
            # Post-process the extracted time
            time_str = post_process_time(time_str)
            
            if time_str and time_str != "Not found":
                return time_str
    
    # Fallback: Look for any time-like patterns in the text
    fallback_patterns = [
        # Any number followed by AM/PM
        r'(?i)(\d{1,2}\s*(?:AM|PM|am|pm))',
        # Any time-like number pattern
        r'(\d{1,2}[:.]\d{2})',
        # Just numbers that might be hours
        r'(?i)(?:at|@)\s*(\d{1,2})',
    ]
    
    for pattern in fallback_patterns:
        match = re.search(pattern, processed_text)
        if match:
            time_str = match.group(1).strip()
            time_str = post_process_time(time_str)
            if time_str and time_str != "Not found":
                return time_str
    
    return "Not found"
    
def extract_venue(text):
    """Extract venue information using comprehensive regex patterns - IMPROVED VERSION"""
    
    def clean_venue_text(venue_text):
        """Clean and validate extracted venue text"""
        if not venue_text:
            return None
            
        venue_text = venue_text.strip()
        
        # Remove common prefixes that might be captured
        venue_text = re.sub(r'^(?i)(?:at|in|the|venue|location|place|address|held at|taking place at)[:.\s]*', '', venue_text)
        
        # Remove trailing punctuation and clean up
        venue_text = re.sub(r'[,.:;!?]+$', '', venue_text)
        venue_text = re.sub(r'\s+', ' ', venue_text).strip()
        
        # Skip if it's too short (likely not a venue) or contains mostly numbers/dates
        if len(venue_text) < 3:
            return None
            
        # Skip if it looks like a date, time, or phone number
        if re.match(r'^[\d\s\-/:.]+$', venue_text):
            return None
            
        # Skip common false positives
        false_positives = [
            r'(?i)^(?:date|time|contact|phone|email|price|free|paid|registration)$',
            r'(?i)^(?:am|pm|\d{1,2}:\d{2}|\d{4})$',
            r'(?i)^(?:january|february|march|april|may|june|july|august|september|october|november|december)$'
        ]
        
        for pattern in false_positives:
            if re.match(pattern, venue_text):
                return None
        
        # Limit length to avoid capturing too much text
        if len(venue_text) > 150:
            # Try to find a reasonable breaking point
            words = venue_text.split()
            if len(words) > 15:
                venue_text = ' '.join(words[:15]) + '...'
        
        return venue_text
    
    # Preprocess text to handle common OCR issues
    processed_text = text.replace('\n', ' | ')  # Replace newlines with separators for better parsing
    
    # Comprehensive venue extraction patterns (ordered by priority/specificity)
    venue_patterns = [
        # Explicit venue/location labels
        r'(?i)venue\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)location\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)place\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)address\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)where\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)held\s+at\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        r'(?i)taking\s+place\s+at\s*[:.]?\s*([^|\n]{3,80})(?=\s*\||$|\n)',
        
        # City, Country patterns (like your examples)
        r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "Zurich, Switzerland"
        
        # "At" patterns with various venue types
        r'(?i)at\s+([^|\n]*?(?:hall|center|centre|auditorium|stadium|arena|theater|theatre|hotel|conference|room|building|campus|university|college|school|library|museum|gallery|club|bar|restaurant|cafe|park|ground|complex|plaza|square|convention|expo|fairground|facility|institute|academy|church|temple|mosque|cathedral|chapel)(?:\s+[^|\n]*?)?)(?=\s*\||$|\n|[.,:;!?])',
        
        # Common venue types without "at"
        r'(?i)\b([A-Z][^|\n]*?(?:hall|center|centre|auditorium|stadium|arena|theater|theatre|hotel|conference\s+(?:room|hall)|convention\s+(?:center|centre)|expo\s+(?:center|centre)|community\s+(?:center|centre|hall)|cultural\s+(?:center|centre)|sports\s+(?:center|centre|complex)|civic\s+(?:center|centre)|town\s+hall|city\s+hall))\b',
        
        # Educational institutions
        r'(?i)\b([A-Z][^|\n]*?(?:university|college|school|institute|academy|campus)(?:\s+of\s+[^|\n]*?)?)\b',
        
        # Downtown/area patterns (like "DOWNTOWN PETERBOROUGH")
        r'(?i)\b((?:downtown|uptown|central|north|south|east|west|upper|lower)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        
        # Hotel patterns
        r'(?i)\b([A-Z][^|\n]*?hotel(?:\s+[^|\n]*?)?)\b',
        
        # Generic place names (proper nouns that could be venues)
        r'(?i)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}(?:\s+(?:Hall|Center|Centre|Building|Complex|Plaza|Square|Gardens?|Park)))\b',
        
        # Address-like patterns (numbers + street names)
        r'(?i)\b(\d+\s+[A-Z][^|\n]*?(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|place|pl|court|ct)(?:\s+[^|\n]*?)?)\b',
        
        # Venue names that end with common suffixes
        r'(?i)\b([A-Z][^|\n]*?(?:centre|center|hall|arena|stadium|theater|theatre|auditorium|pavilion|complex|plaza|gardens?|park|ground|academy|institute|gallery|museum|library|club|lodge|manor|palace|castle|fort|tower|square))\b',
        
        # Room/Floor patterns
        r'(?i)((?:room|floor|level|suite|block|wing|section)\s+[A-Z0-9][^|\n]*?)\b',
        
        # Generic proper noun patterns (2-4 words starting with capital letters)
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b(?=.*(?:hall|center|centre|auditorium|stadium|arena|theater|theatre|hotel|conference|university|college|school|institute|academy|building|complex|plaza|square|park|ground|club|bar|restaurant|cafe|museum|gallery|library|church|temple|mosque|cathedral)|\s*[,.]|\s*$)',
    ]
    
    # Try each pattern and collect potential venues
    potential_venues = []
    
    for pattern in venue_patterns:
        matches = re.finditer(pattern, processed_text)
        for match in matches:
            venue_candidate = match.group(1).strip()
            cleaned_venue = clean_venue_text(venue_candidate)
            
            if cleaned_venue and len(cleaned_venue) > 2:
                # Add confidence scoring based on pattern type
                confidence = 1.0
                
                # Higher confidence for explicit venue labels
                if any(label in pattern for label in ['venue', 'location', 'address', 'place']):
                    confidence = 1.0
                # Medium confidence for "at" patterns and venue types
                elif 'at\\s+' in pattern or any(vtype in pattern for vtype in ['hall', 'center', 'hotel', 'university']):
                    confidence = 0.8
                # Lower confidence for generic patterns
                else:
                    confidence = 0.6
                
                potential_venues.append((cleaned_venue, confidence))
    
    # Remove duplicates and sort by confidence
    unique_venues = {}
    for venue, conf in potential_venues:
        venue_lower = venue.lower()
        if venue_lower not in unique_venues or unique_venues[venue_lower][1] < conf:
            unique_venues[venue_lower] = (venue, conf)
    
    if unique_venues:
        # Return the venue with highest confidence
        best_venue = max(unique_venues.values(), key=lambda x: x[1])
        return best_venue[0]
    
    # Fallback: Look for any proper nouns that might be venues
    # Look for sequences of capitalized words (2-4 words)
    fallback_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    fallback_matches = re.findall(fallback_pattern, text)
    
    for match in fallback_matches:
        cleaned = clean_venue_text(match)
        if cleaned and len(cleaned) > 5:  # Slightly longer minimum for fallback
            # Additional filtering for fallback matches
            if not re.search(r'(?i)^(?:january|february|march|april|may|june|july|august|september|october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', cleaned):
                return cleaned
    
    return "Not found"

def extract_profession(text):
    """Extract profession or target audience information with comprehensive patterns"""
    
    # Normalize text for better matching
    text_lower = text.lower()
    
    # Direct profession keywords and their mappings
    profession_keywords = {
        'student': ['student', 'students', 'undergraduate', 'graduate', 'phd', 'doctoral', 'scholar', 'learner'],
        'researcher': ['researcher', 'researchers', 'research', 'scientist', 'scientists', 'investigator', 'academic', 'academics'],
        'professional': ['professional', 'professionals', 'practitioner', 'practitioners', 'expert', 'experts'],
        'developer': ['developer', 'developers', 'programmer', 'programmers', 'coder', 'coders', 'engineer', 'engineers'],
        'teacher': ['teacher', 'teachers', 'educator', 'educators', 'instructor', 'instructors', 'faculty'],
        'doctor': ['doctor', 'doctors', 'physician', 'physicians', 'medical', 'healthcare'],
        'artist': ['artist', 'artists', 'creative', 'creatives', 'designer', 'designers'],
        'entrepreneur': ['entrepreneur', 'entrepreneurs', 'startup', 'business owner', 'founder'],
        'manager': ['manager', 'managers', 'executive', 'executives', 'leader', 'leadership'],
    }
    
    # Extended patterns for profession extraction
    profession_patterns = [
        # Direct targeting patterns
        r'(?i)(?:for|targeting|aimed\s+at|intended\s+for|designed\s+for)\s+(.*?(?:students?|researchers?|professionals?|developers?|engineers?|doctors?|teachers?|artists?|musicians?|entrepreneurs?|designers?|managers?|executives?|academics?|scholars?|practitioners?|scientists?))',
        
        # Invitation patterns
        r'(?i)(.*?(?:students?|researchers?|professionals?|developers?|engineers?|doctors?|teachers?|artists?|musicians?|entrepreneurs?|designers?|managers?|executives?|academics?|scholars?|practitioners?|scientists?))\s+(?:are\s+)?(?:invited|welcome|encouraged|requested)',
        
        # Call for participation patterns
        r'(?i)(?:call\s+for|seeking|inviting|looking\s+for)\s+(.*?(?:students?|researchers?|professionals?|paper\s+submission|abstract\s+submission|presentation))',
        
        # Paper submission patterns (indicating academic/research context)
        r'(?i)(paper\s+submission|abstract\s+submission|research\s+paper|manuscript\s+submission|call\s+for\s+papers)',
        
        # Registration patterns
        r'(?i)(?:registration\s+(?:open\s+)?for|register\s+(?:now\s+)?for)\s+(.*?(?:students?|researchers?|professionals?|participants?))',
        
        # General audience patterns
        r'(?i)(?:open\s+to\s+all|all\s+are\s+welcome|everyone\s+welcome)\s*(.*?)(?:\n|$|\.)',
        
        # Context-based patterns (conference, workshop, etc.)
        r'(?i)(?:conference|workshop|seminar|symposium|congress)\s+(?:for|on)\s+(.*?)(?:\n|$|\.)',
        
        # Membership or association patterns
        r'(?i)(?:member|members)\s+of\s+(.*?)(?:\n|$|\.)',
        
        # Experience level patterns
        r'(?i)(?:beginner|intermediate|advanced|expert)\s+(.*?)(?:\n|$|\.)',
        
        # Discipline-specific patterns
        r'(?i)(?:computer\s+science|engineering|medical|business|arts?|science)\s+(students?|professionals?|researchers?)',
    ]
    
    found_professions = set()
    
    # Try each pattern
    for pattern in profession_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            matched_text = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()
            
            # Handle paper submission case specifically
            if 'paper submission' in matched_text.lower() or 'abstract submission' in matched_text.lower():
                found_professions.add('Students/Researchers')
                continue
            
            # Clean and process the matched text
            matched_text = clean_text(matched_text)
            if len(matched_text) > 100:  # Limit length
                matched_text = ' '.join(matched_text.split()[:10])
            
            # Map to standard profession categories
            mapped_profession = map_to_standard_profession(matched_text, profession_keywords)
            if mapped_profession:
                found_professions.add(mapped_profession)
            else:
                found_professions.add(matched_text)
    
    # Look for individual keywords in the entire text
    for category, keywords in profession_keywords.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                found_professions.add(category.title())
    
    # Special handling for common academic contexts
    academic_indicators = [
        'conference', 'symposium', 'workshop', 'seminar', 'congress', 
        'journal', 'publication', 'research', 'academic', 'university', 'college'
    ]
    
    if any(indicator in text_lower for indicator in academic_indicators):
        if 'paper' in text_lower or 'abstract' in text_lower or 'submission' in text_lower:
            found_professions.add('Students/Researchers')
    
    # Remove duplicates and format result
    if found_professions:
        # Remove generic terms if more specific ones exist
        specific_terms = found_professions - {'professional', 'participants', 'everyone'}
        if specific_terms:
            found_professions = specific_terms
        
        return ', '.join(sorted(found_professions))
    
    return "Not specified"


def map_to_standard_profession(text, profession_keywords):
    """Map extracted text to standard profession categories"""
    text_lower = text.lower()
    
    for category, keywords in profession_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category.title()
    
    return None

def determine_event_type(text):
    """Determine if the event is online or offline"""
    online_patterns = [
        r'(?i)online',
        r'(?i)virtual',
        r'(?i)zoom',
        r'(?i)webinar',
        r'(?i)web\s+conference',
        r'(?i)livestream',
        r'(?i)live\s+stream',
        r'(?i)google\s+meet',
        r'(?i)microsoft\s+teams',
        r'(?i)webex',
    ]
    
    for pattern in online_patterns:
        if re.search(pattern, text):
            return "Online"
    
    # If venue is specified, it's likely offline
    if extract_venue(text) != "Not found":
        return "Offline"
    
    return "Not specified"

def extract_phone_numbers(text):
    """Extract contact phone numbers"""
    phone_patterns = [
        r'(?i)(?:phone|mobile|contact|call|tel|telephone)\s*:?\s*(\+?\d[\d\s\-().]{7,})',
        r'(?i)(?:phone|mobile|contact|call|tel|telephone)\s*:?\s*(\+?\d{1,4}[\s\-()]*\d{3,4}[\s\-()]*\d{3,4})',
        r'(?<!\d)(\+?\d{10,12})(?!\d)',
        r'(?<!\d)(\+?\d{1,4}[\s\-()]*\d{3,4}[\s\-()]*\d{3,4})(?!\d)',
    ]
    
    phone_numbers = []
    for pattern in phone_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            phone = match.group(1).strip()
            # Clean up the phone number
            phone = re.sub(r'[^\d+]', '', phone)
            if len(phone) >= 10:  # Only include if it's a valid length
                phone_numbers.append(phone)
    
    if phone_numbers:
        return ', '.join(phone_numbers)
    
    return "Not found"

def extract_email(text):
    """Extract all email addresses from text with improved patterns"""
    
    # Comprehensive email pattern that handles various formats
    email_patterns = [
        # Standard email format
        r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b',
        
        # Email with spaces (OCR artifacts): "user @ domain . com"
        r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?\s*@\s*[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\s*\.\s*[a-zA-Z]{2,}\b',
        
        # Email patterns with context
        r'(?i)(?:email|e-mail|contact|write\s+to|send\s+to|reach\s+(?:us\s+)?(?:at|out))\s*:?\s*([a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,})',
        
        # Multiple emails in a line separated by common delimiters
        r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}(?:\s*[,;|&/]\s*[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,})*',
    ]
    
    found_emails = set()
    
    # Apply each pattern
    for pattern in email_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.lastindex and match.lastindex >= 1:
                email_text = match.group(1)
            else:
                email_text = match.group(0)
            
            # Clean up spaces in email (OCR artifacts)
            email_text = re.sub(r'\s+', '', email_text)
            
            # Split multiple emails if they're in one match
            potential_emails = re.split(r'[,;|&/\s]+', email_text)
            
            for email in potential_emails:
                email = email.strip()
                if validate_email(email):
                    found_emails.add(email.lower())
    
    # Convert to sorted list to ensure consistent output
    unique_emails = sorted(list(found_emails))
    
    if unique_emails:
        return ', '.join(unique_emails)
    
    return "Not found"


def validate_email(email):
    """Validate if the extracted text is a proper email address"""
    # Basic email validation
    email_regex = r'^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        return False
    
    # Additional checks
    if len(email) < 5 or len(email) > 254:  # RFC 5321 limits
        return False
    
    # Check for reasonable domain
    domain = email.split('@')[1]
    if '.' not in domain or len(domain.split('.')[-1]) < 2:
        return False
    
    return True


def extract_social_media(text):
    """Extract social media links and handles"""
    social_patterns = [
        r'(?i)(?:facebook|fb)\.com/\S+',
        r'(?i)(?:instagram|ig)\.com/\S+',
        r'(?i)(?:twitter|x)\.com/\S+',
        r'(?i)linkedin\.com/\S+',
        r'(?i)youtube\.com/\S+',
        r'(?i)@\w+',  # Common social media handle format
    ]
    
    social_media = []
    for pattern in social_patterns:
        matches = re.findall(pattern, text)
        social_media.extend(matches)
    
    if social_media:
        return ', '.join(social_media)
    
    return "Not found"

def extract_price(text):
    """Extract price information with support for multiple currencies and formats"""
    
    # Currency symbols and abbreviations
    currency_patterns = {
        'INR': [r'₹', r'Rs\.?', r'INR', r'Rupees?'],
        'USD': [r'\$', r'USD', r'Dollars?'],
        'EUR': [r'€', r'EUR', r'Euros?'],
        'GBP': [r'£', r'GBP', r'Pounds?'],
        'JPY': [r'¥', r'JPY', r'Yen'],
    }
    
    # Comprehensive price patterns
    price_patterns = []
    
    # Generate patterns for each currency
    for currency_code, symbols in currency_patterns.items():
        for symbol in symbols:
            # Currency before amount: $100, Rs. 500
            price_patterns.extend([
                rf'(?i)(?:price|fee|cost|ticket|registration|entry)\s*:?\s*{symbol}\s*(\d+(?:[,.]\d+)?)',
                rf'(?i){symbol}\s*(\d+(?:[,.]\d+)?)',
                rf'(?i)(?:price|fee|cost|ticket|registration|entry)\s*:?\s*(\d+(?:[,.]\d+)?)\s*{symbol}',
                rf'(?i)(\d+(?:[,.]\d+)?)\s*{symbol}',
            ])
    
    # Additional patterns for price ranges and complex formats
    additional_patterns = [
        # Price ranges: $100-200, Rs. 500 to 1000
        r'(?i)(?:price|fee|cost|ticket|registration|entry)\s*:?\s*(?:Rs\.?|₹|INR|USD|\$|€|EUR|£|GBP|¥|JPY)?\s*(\d+(?:[,.]\d+)?)\s*(?:to|-|–)\s*(?:Rs\.?|₹|INR|USD|\$|€|EUR|£|GBP|¥|JPY)?\s*(\d+(?:[,.]\d+)?)',
        
        # Multiple price tiers: Student: $10, Professional: $50
        r'(?i)((?:student|professional|academic|member|non-member|early\s+bird|regular)\s*:?\s*(?:Rs\.?|₹|INR|USD|\$|€|EUR|£|GBP|¥|JPY)?\s*\d+(?:[,.]\d+)?)',
        
        # Price with context: Registration fee is $100
        r'(?i)(?:registration|entry|participation|ticket)\s+(?:fee|cost|price)\s+(?:is|of)?\s*(?:Rs\.?|₹|INR|USD|\$|€|EUR|£|GBP|¥|JPY)?\s*(\d+(?:[,.]\d+)?)',
        
        # Just numbers that might be prices (when near price-related words)
        r'(?i)(?:price|fee|cost|ticket|registration|entry|pay|payment)\s*:?\s*(\d+(?:[,.]\d+)?)',
    ]
    
    price_patterns.extend(additional_patterns)
    
    found_prices = []
    
    # Try each pattern
    for pattern in price_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get the surrounding context to check for currency and free indicators
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            surrounding_text = text[start_pos:end_pos].lower()
            
            # Check if it's free
            if re.search(r'(?i)\b(?:free|no\s+(?:charge|fee|cost)|complimentary|gratis)\b', surrounding_text):
                found_prices.append("Free")
                continue
            
            # Extract price components
            if match.lastindex == 2:  # Price range
                price1, price2 = match.groups()
                currency = extract_currency_from_context(surrounding_text)
                found_prices.append(f"{currency}{price1}-{price2}")
            else:
                price = match.group(1) if match.lastindex >= 1 else match.group(0)
                price = re.sub(r'[^\d.,]', '', price)  # Clean non-numeric characters
                
                if price and re.match(r'\d', price):  # Ensure it starts with a digit
                    currency = extract_currency_from_context(surrounding_text)
                    found_prices.append(f"{currency}{price}")
    
    # Check for free event indicators
    free_patterns = [
        r'(?i)\b(?:free\s+(?:entry|admission|event|registration)|no\s+(?:charge|fee|cost)|entry\s+free|admission\s+free|complimentary|gratis)\b'
    ]
    
    for pattern in free_patterns:
        if re.search(pattern, text):
            found_prices.append("Free")
            break
    
    # Remove duplicates while preserving order
    unique_prices = list(dict.fromkeys(found_prices))
    
    if unique_prices:
        return ' | '.join(unique_prices)  # Use | to separate multiple prices
    
    return "Not found"


def extract_currency_from_context(text):
    """Extract currency symbol from surrounding text"""
    currency_map = {
        '₹': '₹', 'rs.': '₹', 'rs': '₹', 'inr': '₹', 'rupee': '₹',
        '$': '$', 'usd': '$', 'dollar': '$',
        '€': '€', 'eur': '€', 'euro': '€',
        '£': '£', 'gbp': '£', 'pound': '£',
        '¥': '¥', 'jpy': '¥', 'yen': '¥',
    }
    
    for key, symbol in currency_map.items():
        if key in text.lower():
            return symbol
    
    return ''  # No currency symbol found


def extract_poster_info(image):
    """Main function to extract all information from poster image"""
    try:
        # Make sure we have a valid image
        if image is None:
            return "No image provided. Please upload an image.", "{}", ""
            
        # Convert image to PIL format if needed and save temporarily
        import tempfile
        from PIL import Image
        import os
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_filename = temp_file.name
        temp_file.close()
        
        # Convert numpy array to PIL Image and save
        if isinstance(image, np.ndarray):
            img = Image.fromarray(image.astype('uint8'))
            img.save(temp_filename)
        else:
            # If it's already a PIL image
            image.save(temp_filename)
            
        # Process the image with DocTR
        doc = DocumentFile.from_images([temp_filename])
        result = model(doc)
        
        # Clean up the temporary file
        os.unlink(temp_filename)
        
        # Extract all text from the document
        extracted_text = ""
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        extracted_text += word.value + " "
                    extracted_text += "\n"
                extracted_text += "\n"
        
        # Extract key information using the improved functions
        event_name = extract_event_name(extracted_text)
        date = extract_date(extracted_text)
        time = extract_time(extracted_text)  # This now uses the improved function
        venue = extract_venue(extracted_text)
        profession = extract_profession(extracted_text)
        event_type = determine_event_type(extracted_text)
        phone = extract_phone_numbers(extracted_text)
        email = extract_email(extracted_text)
        social_media = extract_social_media(extracted_text)
        price = extract_price(extracted_text)
        
        # Create output in both JSON and CSV formats
        info_dict = {
            "Event Name": event_name,
            "Date": date,
            "Time": time,
            "Venue": venue,
            "Profession/Target Audience": profession,
            "Event Type": event_type,
            "Contact Number": phone,
            "Email": email,
            "Social Media": social_media,
            "Price": price
        }
        
        # Convert to JSON
        json_output = json.dumps(info_dict, indent=4)
        
        # Convert to CSV
        df = pd.DataFrame([info_dict])
        csv_output = df.to_csv(index=False)
        
        return extracted_text, json_output, csv_output
    except Exception as e:
        return f"Error processing image: {str(e)}", "{}", ""

# Create Gradio interface
with gr.Blocks(title="Event Poster Information Extractor") as demo:
    gr.Markdown("# 📢 Event Poster Information Extractor")
    gr.Markdown("""
    Upload an event poster image to extract key information such as event name, date, time, venue, 
    contact details, and pricing. The system uses DocTR for OCR and regex patterns for information extraction.
    
    **Enhanced Date Extraction**: Now handles various date formats including:
    - Date ranges (January 18-19, 2025)
    - Day names with dates (Saturday May 20th, THURSDAY 2/20)
    - Common misspellings (Feburary → February)
    - Partial dates and flexible formatting
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            input_image = gr.Image(label="Upload Poster Image")
            extract_btn = gr.Button("Extract Information", variant="primary")
        
        with gr.Column(scale=2):
            with gr.Tab("Extracted Text"):
                text_output = gr.Textbox(label="Raw Extracted Text", lines=10)
            
            with gr.Tab("JSON Output"):
                json_output = gr.JSON(label="Structured Information (JSON)")
            
            with gr.Tab("CSV Output"):
                csv_output = gr.Textbox(label="Structured Information (CSV)", lines=10)
    
    extract_btn.click(
        fn=extract_poster_info,
        inputs=[input_image],
        outputs=[text_output, json_output, csv_output]
    )
    
    gr.Markdown("""
    ## How it works
    
    1. The system uses DocTR (Document Text Recognition) for OCR to extract all text from the poster
    2. Specialized regex patterns identify and extract key information
    3. Enhanced date extraction handles various formats and common OCR errors
    4. The extracted data is provided in both JSON and CSV formats
    
    ## Date Extraction Improvements
    
    - **Date ranges**: "January 18-19, 2025", "18-19 January 2025"
    - **Day names**: "Saturday May 20th", "SAT. MAY20TH"
    - **Numeric formats**: "THURSDAY 2/20", "28th February 2025"
    - **Misspellings**: Handles "Feburary" and other common OCR errors
    - **Partial dates**: Extracts available components when full date isn't found
    
    ## Tips for best results
    
    - Use clear, high-resolution images of posters
    - Ensure the poster has good contrast between text and background
    - Make sure key information is visible and not obscured
    """)

# Launch the app
if __name__ == "__main__":
    demo.launch()