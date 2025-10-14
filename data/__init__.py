"""
Модуль для работы со статичными данными из JSON файлов
"""
import json
import os
from typing import List, Dict, Optional

# Путь к директории с данными
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(filename: str) -> dict:
    """Загрузка данных из JSON файла"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_courses() -> List[Dict]:
    """Получить все курсы"""
    data = load_json('courses.json')
    return data.get('courses', [])


def get_course_by_slug(slug: str) -> Optional[Dict]:
    """Получить курс по slug"""
    courses = get_all_courses()
    for course in courses:
        if course['slug'] == slug:
            return course
    return None


def get_active_courses() -> List[Dict]:
    """Получить активные курсы"""
    courses = get_all_courses()
    return [c for c in courses if c.get('is_active', True)]


def get_tariff_by_id(course_slug: str, tariff_id: str) -> Optional[Dict]:
    """Получить тариф по ID"""
    course = get_course_by_slug(course_slug)
    if not course:
        return None
    
    for tariff in course.get('tariffs', []):
        if tariff['id'] == tariff_id:
            return tariff
    return None


def get_all_consultations() -> List[Dict]:
    """Получить все консультации"""
    data = load_json('consultations.json')
    return data.get('consultations', [])


def get_consultation_by_slug(slug: str) -> Optional[Dict]:
    """Получить консультацию по slug"""
    consultations = get_all_consultations()
    for consultation in consultations:
        if consultation['slug'] == slug:
            return consultation
    return None


def get_active_consultations() -> List[Dict]:
    """Получить активные консультации"""
    consultations = get_all_consultations()
    return [c for c in consultations if c.get('is_active', True)]


def get_consultations_by_category(category: str) -> List[Dict]:
    """Получить консультации по категории"""
    consultations = get_active_consultations()
    return [c for c in consultations if c.get('category') == category]


def get_consultation_option(consultation_slug: str, option_id: str) -> Optional[Dict]:
    """Получить опцию консультации"""
    consultation = get_consultation_by_slug(consultation_slug)
    if not consultation:
        return None
    
    for option in consultation.get('options', []):
        if option['id'] == option_id:
            return option
    return None


# Для удобства экспортируем функции
__all__ = [
    'get_all_courses',
    'get_course_by_slug',
    'get_active_courses',
    'get_tariff_by_id',
    'get_all_consultations',
    'get_consultation_by_slug',
    'get_active_consultations',
    'get_consultations_by_category',
    'get_consultation_option',
]

