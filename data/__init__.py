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


def save_json(filename: str, data: dict) -> None:
    """Сохранение данных в JSON файл"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def get_all_guides() -> List[Dict]:
    """Получить все гайды из JSON"""
    data = load_json('guides.json')
    return data.get('guides', [])


def get_guide_by_id(guide_id: str) -> Optional[Dict]:
    """Получить гайд по ID"""
    guides = get_all_guides()
    for guide in guides:
        if guide['id'] == guide_id:
            return guide
    return None


def get_active_guides() -> List[Dict]:
    """Получить активные гайды из JSON"""
    guides = get_all_guides()
    return [g for g in guides if g.get('is_active', True)]


# ==================== Функции записи ====================

def save_courses(courses: List[Dict]) -> None:
    """Сохранить курсы в JSON"""
    data = {'courses': courses}
    save_json('courses.json', data)


def save_course(course: Dict) -> None:
    """Сохранить/обновить один курс"""
    courses = get_all_courses()
    
    # Ищем существующий курс
    found = False
    for i, c in enumerate(courses):
        if c['id'] == course['id']:
            courses[i] = course
            found = True
            break
    
    # Если не найден - добавляем
    if not found:
        courses.append(course)
    
    save_courses(courses)


def delete_course(course_id: str) -> bool:
    """Удалить курс"""
    courses = get_all_courses()
    new_courses = [c for c in courses if c['id'] != course_id]
    
    if len(new_courses) < len(courses):
        save_courses(new_courses)
        return True
    return False


def save_consultations(consultations: List[Dict]) -> None:
    """Сохранить консультации в JSON"""
    data = {'consultations': consultations}
    save_json('consultations.json', data)


def save_consultation(consultation: Dict) -> None:
    """Сохранить/обновить одну консультацию"""
    consultations = get_all_consultations()
    
    # Ищем существующую консультацию
    found = False
    for i, c in enumerate(consultations):
        if c['id'] == consultation['id']:
            consultations[i] = consultation
            found = True
            break
    
    # Если не найдена - добавляем
    if not found:
        consultations.append(consultation)
    
    save_consultations(consultations)


def delete_consultation(consultation_id: str) -> bool:
    """Удалить консультацию"""
    consultations = get_all_consultations()
    new_consultations = [c for c in consultations if c['id'] != consultation_id]
    
    if len(new_consultations) < len(consultations):
        save_consultations(new_consultations)
        return True
    return False


def save_guides(guides: List[Dict]) -> None:
    """Сохранить гайды в JSON"""
    data = {'guides': guides}
    save_json('guides.json', data)


def save_guide(guide: Dict) -> None:
    """Сохранить/обновить один гайд"""
    guides = get_all_guides()
    
    # Ищем существующий гайд
    found = False
    for i, g in enumerate(guides):
        if g['id'] == guide['id']:
            guides[i] = guide
            found = True
            break
    
    # Если не найден - добавляем
    if not found:
        guides.append(guide)
    
    save_guides(guides)


def delete_guide(guide_id: str) -> bool:
    """Удалить гайд"""
    guides = get_all_guides()
    new_guides = [g for g in guides if g['id'] != guide_id]
    
    if len(new_guides) < len(guides):
        save_guides(new_guides)
        return True
    return False


# ==================== Отзывы ====================

def get_all_reviews() -> List[Dict]:
    """Получить все отзывы из JSON"""
    data = load_json('reviews.json')
    return data.get('reviews', [])


def get_review_by_id(review_id: str) -> Optional[Dict]:
    """Получить отзыв по ID"""
    reviews = get_all_reviews()
    for review in reviews:
        if review['id'] == review_id:
            return review
    return None


def get_active_reviews() -> List[Dict]:
    """Получить активные отзывы из JSON"""
    reviews = get_all_reviews()
    return [r for r in reviews if r.get('is_active', True)]


def save_reviews(reviews: List[Dict]) -> None:
    """Сохранить отзывы в JSON"""
    data = {'reviews': reviews}
    save_json('reviews.json', data)


def save_review(review: Dict) -> None:
    """Сохранить/обновить один отзыв"""
    reviews = get_all_reviews()
    
    # Ищем существующий отзыв
    found = False
    for i, r in enumerate(reviews):
        if r['id'] == review['id']:
            reviews[i] = review
            found = True
            break
    
    # Если не найден - добавляем
    if not found:
        reviews.append(review)
    
    save_reviews(reviews)


def delete_review(review_id: str) -> bool:
    """Удалить отзыв"""
    reviews = get_all_reviews()
    new_reviews = [r for r in reviews if r['id'] != review_id]
    
    if len(new_reviews) < len(reviews):
        save_reviews(new_reviews)
        return True
    return False


# ==================== Материалы курсов ====================

def get_course_materials(course_slug: str) -> Optional[Dict]:
    """Получить материалы курса"""
    try:
        data = load_json('course_materials.json')
        materials = data.get('materials', {})
        return materials.get(course_slug)
    except Exception:
        return None


def get_course_modules(course_slug: str) -> List[Dict]:
    """Получить модули курса"""
    materials = get_course_materials(course_slug)
    if not materials:
        return []
    return materials.get('modules', [])


def get_module_by_id(course_slug: str, module_id: str) -> Optional[Dict]:
    """Получить модуль по ID"""
    modules = get_course_modules(course_slug)
    for module in modules:
        if module['id'] == module_id:
            return module
    return None


def get_lesson_by_id(course_slug: str, module_id: str, lesson_id: str) -> Optional[Dict]:
    """Получить урок по ID"""
    module = get_module_by_id(course_slug, module_id)
    if not module:
        return None
    
    for lesson in module.get('lessons', []):
        if lesson['id'] == lesson_id:
            return lesson
    return None


def save_course_materials(course_slug: str, materials: Dict) -> None:
    """Сохранить материалы курса"""
    try:
        data = load_json('course_materials.json')
    except:
        data = {'materials': {}}
    
    if 'materials' not in data:
        data['materials'] = {}
    
    data['materials'][course_slug] = materials
    save_json('course_materials.json', data)


def add_module_to_course(course_slug: str, module: Dict) -> None:
    """Добавить модуль к курсу"""
    materials = get_course_materials(course_slug)
    if not materials:
        materials = {'modules': []}
    
    if 'modules' not in materials:
        materials['modules'] = []
    
    materials['modules'].append(module)
    save_course_materials(course_slug, materials)


def update_module(course_slug: str, module_id: str, updated_module: Dict) -> bool:
    """Обновить модуль"""
    materials = get_course_materials(course_slug)
    if not materials or 'modules' not in materials:
        return False
    
    for i, module in enumerate(materials['modules']):
        if module['id'] == module_id:
            materials['modules'][i] = updated_module
            save_course_materials(course_slug, materials)
            return True
    
    return False


def delete_module(course_slug: str, module_id: str) -> bool:
    """Удалить модуль"""
    materials = get_course_materials(course_slug)
    if not materials or 'modules' not in materials:
        return False
    
    original_len = len(materials['modules'])
    materials['modules'] = [m for m in materials['modules'] if m['id'] != module_id]
    
    if len(materials['modules']) < original_len:
        save_course_materials(course_slug, materials)
        return True
    
    return False


def add_lesson_to_module(course_slug: str, module_id: str, lesson: Dict) -> bool:
    """Добавить урок в модуль"""
    materials = get_course_materials(course_slug)
    if not materials or 'modules' not in materials:
        return False
    
    for module in materials['modules']:
        if module['id'] == module_id:
            if 'lessons' not in module:
                module['lessons'] = []
            module['lessons'].append(lesson)
            save_course_materials(course_slug, materials)
            return True
    
    return False


def update_lesson(course_slug: str, module_id: str, lesson_id: str, updated_lesson: Dict) -> bool:
    """Обновить урок"""
    materials = get_course_materials(course_slug)
    if not materials or 'modules' not in materials:
        return False
    
    for module in materials['modules']:
        if module['id'] == module_id:
            for i, lesson in enumerate(module.get('lessons', [])):
                if lesson['id'] == lesson_id:
                    module['lessons'][i] = updated_lesson
                    save_course_materials(course_slug, materials)
                    return True
    
    return False


def delete_lesson(course_slug: str, module_id: str, lesson_id: str) -> bool:
    """Удалить урок"""
    materials = get_course_materials(course_slug)
    if not materials or 'modules' not in materials:
        return False
    
    for module in materials['modules']:
        if module['id'] == module_id:
            original_len = len(module.get('lessons', []))
            module['lessons'] = [l for l in module.get('lessons', []) if l['id'] != lesson_id]
            
            if len(module['lessons']) < original_len:
                save_course_materials(course_slug, materials)
                return True
    
    return False


# Для удобства экспортируем функции
__all__ = [
    # Чтение курсов
    'get_all_courses',
    'get_course_by_slug',
    'get_active_courses',
    'get_tariff_by_id',
    # Материалы курсов
    'get_course_materials',
    'get_course_modules',
    'get_module_by_id',
    'get_lesson_by_id',
    # Редактирование материалов курсов
    'save_course_materials',
    'add_module_to_course',
    'update_module',
    'delete_module',
    'add_lesson_to_module',
    'update_lesson',
    'delete_lesson',
    # Консультации
    'get_all_consultations',
    'get_consultation_by_slug',
    'get_active_consultations',
    'get_consultations_by_category',
    'get_consultation_option',
    # Гайды
    'get_all_guides',
    'get_guide_by_id',
    'get_active_guides',
    # Отзывы
    'get_all_reviews',
    'get_review_by_id',
    'get_active_reviews',
    # Запись
    'save_course',
    'save_courses',
    'delete_course',
    'save_consultation',
    'save_consultations',
    'delete_consultation',
    'save_guide',
    'save_guides',
    'delete_guide',
    'save_review',
    'save_reviews',
    'delete_review',
]

