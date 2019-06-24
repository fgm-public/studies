import os
import re
import json
import time
import pandas
# install openpyxl
import pickle
import pymongo
import cProfile
import requests
import statistics
import collections
from tqdm import tqdm
from bs4 import BeautifulSoup
##from pymongo import MongoClient


class VacancyHandler:
    ''' Сlass is designed to collect and analyze information about vacancies
    from HeadHunter REST API '''

#---------------------------------------------------------------------------------------------------------
#---Initializations---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Base HeadHunter API-url for vacancy retrievement
    api_url = 'https://api.hh.ru/vacancies'

    # Azure CosmoDB db connection string
    mongo_credentials = ('mongodb://1b145613-0ee0-4-231-b9ee:7w3yd'
                         'n0e2aNuqOTCqxa99hHwJcF4kPrkAmEKFtiDHaR1u'
                         'LOca0u25CcEASZnKk1YJHnqfEs1JyPrHe4gEAFkg'
                         'g==@1b145613-0ee0-4-231-b9ee.documents.a'
                         'zure.com:10255/?ssl=true&replicaSet=glob'
                         'aldb')

    # Select certain 'hh_vacancies' db in mongo
    ##mongo_client = pymongo.MongoClient(mongo_credentials)
    ##mongo_db = mongo_client.hh_vacancies
    mongo_db = pymongo.MongoClient(mongo_credentials).hh_vacancies


    def __init__(self,
                # Text to be searched in vacancy to establish a match condition.
                # Occupation name, in main
                search_criteria,
                # Place in vacancy in which match condition will be established
                search_field='name',
                average_salary=200000,
                # Region restriction for vacancy search, for example:
                # Russia(113), Novosibirsk(1202) region
                geo_areas=['1202',]):
        
         #Global path to store pickles and results
        self.store_path = 'D:/store'

        # Text to be searched in vacancy to establish a match condition.
        # Occupation name, in main
        self.search_criteria = search_criteria

        # Region restriction for vacancy search, for example:
        # Russia(113), Novosibirsk(1202) region
        self.search_geo_areas = geo_areas
        
        # Full vacancies batch itself
        self.vacancies = []

        # Names of all vacancies in batch
        self.vacancy_names = None

        # Keyskills (tags) top and all
        self.skills = None
        self.skills_all = None
 
        # Keywords (all english words) top and all
        self.keywords = None
        self.keywords_all = None

        # All subject headings (html 'strongs') from vacancy descriptions
        self.description_sections = None

        # Child elements from all subject headings (html 'strongs')
        self.description_elements_all = None

        # Child elements from top 10 subject headings (html 'strongs')
        self.description_elements = None

        # Child elements from description_sections_top subject headings (html 'strongs')
        self.description_elements_top = None

        # Wordbags formed from self.description_elements
        self.wordbags_all = None
        
        # Wordbags formed from self.description_sections_top
        self.wordbags = None
        
        # Common professional areas in retrieved vacancies
        self.profareas = None
        
        # Specialization areas in retrieved vacancies
        self.profareas_granular = None
        
        # Publication dates
        self.dates = None
        
        # Regions
        self.regions = None
        
        # Required experience
        self.experience = None

        # Employers list with full info: id, vacancies url . . .
        self.employers_full = None
        # Employers list in {name:url} format
        self.employers_brief = None
        
        # Number of unique vacancies among all
        self.unique = None
        
        # HH clusters of vacancies
        self.clusters = None

        # Average salary
        self.average_salary = 0

        # Median salary
        self.median_salary = 0

        # Modal salary
        self.modal_salary = 0

        # Salary groups
        self.salary_groups = {
            'Менее 20000' : 0,
            '20000-30000' : 0,
            '30000-40000' : 0,
            '40000-50000' : 0,
            '50000-60000' : 0,
            '60000-70000' : 0,
            '70000-90000' : 0,
            'Более 90000' : 0
            }

        # Top of 'strong's' dictionary corpus,
        # formed from lots of batches of different vacancies retrieved previously
        self.description_sections_top = frozenset({
            'Требования',
            'Обязанности',
            'Условия',
            'Мы предлагаем',
        })

        self.filter_vocabulary = {

            'Тренды': frozenset({'hi-po',
                                 'agile',
                                 'digital',
                                 'эмпатия',
                                 'коучинг',
                                 'лидерство',
                                 'коллаборация',
                                 'осознанное влияние',
                                 'креативность мышления',
                                 'эмоциональный интеллект',
                                 'управление эффективностью',}),

            'Знания': frozenset({'знание',
                                 'умение',
                                 'навыки',}),

            'Интегратор': frozenset({'честность',
                                     'командная работа',
                                     'коммуникабельность',
                                     'командное лидерство',
                                     'установление контактов',
                                     'управление конфликтами',
                                     'разделение ответственности',
                                     'организаторские способности',}),

            'Производитель': frozenset({'активность',
                                        'целеустремленность',
                                        'последовательность',
                                        'уверенность в себе',
                                        'установка на обучение',
                                        'понимание организации',
                                        'аналитическое мышление',
                                        'ориентация на результат',
                                        'энергетический потенциал',
                                        'профессиональная ответственность',}),

            'Администратор': frozenset({'информирование',
                                        'корпоративность',
                                        'влияние и воздействие',
                                        'ориентация на стандарт',
                                        'концептуальность мышления',
                                        'организованность стресс менеджмент',}),

            'Предприниматель': frozenset({'гибкость',
                                          'адаптируемость',
                                          'принятие решения',
                                          'управление рисками',
                                          'инновационное мышление',
                                          'управление изменениями',
                                          'клиенториентированность',
                                          'стратегическое мышление',
                                          'предпринимательский подход',}),
        }

        # Request to API parameters
        self.search_parameters = {
            'text': self.search_criteria,
            ##'salary': average_salary,
            'area': self.search_geo_areas,
            'per_page': 100,
            'page': 0,
            'clusters': 'true',
            'describe_arguments': 'true',
            }
        
        # Search arguments returned by HH server
        self.search_arguments = None

        if search_field: self.search_parameters['search_field'] = search_field
        #if search_area: self.search_parameters['area'] = search_area

        #Determines when the class instance is freshly created
        #and actually does not contain vacancies yet
        self.__initial = True

    def __len__(self):
        return len(self.vacancies)

    def __getitem__(self, position):
        return self.vacancies[position]

    def __repr__(self):
        return (f"Totally {self.__len__()} vacancies on "
        f"'{self.search_parameters.get('text', 'undefined')}' occupation")

#---------------------------------------------------------------------------------------------------------
#---Retrievers--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Retrieve vacancies from HH
    #---------------------------------------------------------------------------------------------------------
    def _vacancies_retriever(self, delay, number):

        brief_vacancies = []
        current_page = 0
        # Vacancies retrievement batch amount limiter (per_page * number)
        if number is not None: pages_count = int(number)
        else: pages_count = current_page + 1

        while current_page < pages_count:
            self.search_parameters['page'] = current_page
            raw_response = requests.get(VacancyHandler.api_url, params = self.search_parameters)
            response = raw_response.json()
            brief_vacancies += response.get('items')
            if number is None: pages_count = response.get('pages')
            current_page += 1

        self.clusters = response.get('clusters')

        # Collecting urls which link to full vacancy descriptions
        urls = [vacancy.get('url')
            for vacancy in brief_vacancies]

        # Form a list of full vacancies without request delay
        ##self.vacancies = [requests.get(url).json() for url in tqdm(urls)]
        
        # Form a list of full vacancies with request delay
        print("Requesting . . .\n")
        
        for url in tqdm(urls):
            self.vacancies.append(requests.get(url).json())
            time.sleep(int(delay))
        print("\nComplete!\n\n")

        self.search_arguments = response.get('arguments')

        print("\nDo you want to pickle freshly retrieved vacancies ( [y]es, [n]o ) ?")
        answer = input()
        if answer.lower() == 'y':
            self.pickle_vacancies()

        # Now the class instance already contains actual vacancies
        self.__initial = False


    # Announces general information on the response to the request
    # Asks for confirmation for the full retrievement
    # Start full retrievement if confirmed
    #---------------------------------------------------------------------------------------------------------
    def _retrievement_confirmator(self):

        raw_response = requests.get(VacancyHandler.api_url, params = self.search_parameters)
        response = raw_response.json()
        pages_count = response.get('pages')
        
        print(f"\nThere are {pages_count*self.search_parameters['per_page']} vacancies",
              f"on '{self.search_parameters.get('text')}' occupation available on hh.ru",
              f"\n\nRetrieve it now ( [y]es, [n]o ) ?")
        answer = input()
        
        if answer.lower() == 'y':
            print("\nDo you want to get all the vacancies or only part of them ( [a]ll, [p]art ) ?")
            number = None
            answer = input()

            if answer.lower() == 'p':
                print("\nPlease specify desired number of hundreds (e.g. 2 means 200 vacancies)")
                number = input()

            print("\nDo you want to add a delay between requests to api ( [y]es, [n]o ) ?")
            delay = 0
            answer = input()

            if answer.lower() == 'y':
                print("\nPlease specify the delay time in seconds:")
                delay = input()

            print(f"\n\n")
            self._vacancies_retriever(delay, number)

#---------------------------------------------------------------------------------------------------------
#---Store-------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Store object 'vacancies' into file located in 'store_path' path
    #---------------------------------------------------------------------------------------------------------
    def pickle_vacancies(self):

        with open(f"{self.store_path}/{self.search_parameters.get('text')}.pickle", 'wb') as file:
            pickle.dump(self.vacancies, file)


    # Restore object 'vacancies' from file located in 'store_path' path
    #---------------------------------------------------------------------------------------------------------
    def unpickle_vacancies(self, store_path):
        with open(store_path, 'rb') as file:
            self.vacancies += pickle.load(file)
        
        # Now the class instance already contains actual vacancies
        self.__initial = False


    # Stores vacancies to mongodb
    #---------------------------------------------------------------------------------------------------------
    def store_to_mongo(self):

        # Create collection with vacancies occupation name stored in 'search_criteria'
        collection = VacancyHandler.mongo_db[self.search_criteria]
        # Stores insert results in variable
        insert_result = collection.insert_many(self.vacancies)
        ##cursor = collection.find({'salary.from': {'$gt': 30000}})


#---------------------------------------------------------------------------------------------------------
#---Results---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------
 
    # Store analyze results into xlsx file 'search_criteria-vacancies_amount.xlsx'
    # located in 'store_path' path
    #---------------------------------------------------------------------------------------------------------
    def store_results_to_xlsx(self):

        def form_sheet(data, columns, name):
            sheet = pandas.DataFrame(data, columns=columns)
            sheet.to_excel(writer, name, index=False)

        writer = pandas.ExcelWriter(f'{self.store_path}/{self.search_criteria}-{len(self.vacancies)}.xlsx')

        form_sheet(self.vacancy_names, ['Название должности', 'Вхождений'], 'Должности')
        form_sheet(self.skills_all, ['Ключевые навыки (тэги)', 'Вхождений'], 'Ключевые навыки (тэги)')
        form_sheet(self.experience, ['Требуемый опыт', 'Вхождений'], 'Опыт')
        form_sheet(self.keywords_all, ['Продукты|Технологии', 'Вхождений'], 'Продукты|Технологии')
        form_sheet(self.employers_brief.items(), ['Работодатель', 'Ссылка'], 'Работодатели')
        form_sheet(self.regions, ['Регион', 'Вхождений'], 'Регионы')
        form_sheet(self.profareas, ['Профобласть', 'Вхождений'], 'Укрупнённые профобласти')
        form_sheet(self.profareas_granular, ['Специализация', 'Вхождений'], 'Специализации профобластей')
        form_sheet(self.salary_groups.items(), ['Диапазон', 'Вхождений'], 'Зарплатные группы')
        form_sheet([(self.average_salary, self.median_salary, self.modal_salary),],
                   ['Средняя зарплата', 'Медианная зарплата', 'Модальная зарплата'], 'Зарплата')

        for criteria in self.filter_vocabulary['Знания']:
            form_sheet(set(self._by_word_extractor(criteria)),
                       [criteria.capitalize()],
                       criteria.capitalize())

        for criteria in self.description_elements_top:
            form_sheet(set(self.description_elements_top.get(criteria)),
                       [criteria.capitalize()],
                       criteria.capitalize())
        
        form_sheet(self.wordbags_all, ['Слово', 'Вхождений'], 'Мешок слов')

        writer.save()


    # Store custom properties (skills, keywords, etc) into text files located in 'store_path' path
    #---------------------------------------------------------------------------------------------------------
    def store_results_to_files(self):

        self._store_results_text(self.skills_all, 'Навыки')
        self._store_results_text(self.keywords_all, 'Слова')
        self._store_results_text(self.experience, 'Опыт')
        self._store_results_text(self.description_elements, 'Категории (Топ)', sort=True)
        self._store_results_text(self.wordbags, 'Мешки слов')
        self._store_extracted_granular()


    # Store arbitrary result stuff into text files located in 'store_path' path
    #---------------------------------------------------------------------------------------------------------
    def _store_results_text(self, object_tobe_saved, filename, sort=False):

        def store_dict_text(dict_tobe_saved):
            # Files will be named after dict keys
            new_store_path = self.store_path + '/' + filename
            os.makedirs(new_store_path, exist_ok=True)
            
            for file_name, content in dict_tobe_saved.items():
                if content:
                    with open(f"{new_store_path}/{file_name}.txt", 'w', encoding='utf8') as file:
                        if sort is True:
                            file.write("\n".join(sorted([str(item)
                                for item in content], key=len)))
                        else:
                            file.write("\n".join([str(item)
                                for item in content]))
        
        def store_list_text(list_tobe_saved):
            if list_tobe_saved:
                with open(f"{self.store_path}/{filename}.txt", 'w', encoding='utf8') as file:
                        if sort is True:
                            file.write("\n".join(sorted([str(item)
                                for item in list_tobe_saved], key=len)))
                        else:
                            file.write("\n".join([str(item)
                                for item in list_tobe_saved]))

        if type(object_tobe_saved) is dict:
            store_dict_text(object_tobe_saved)
        elif type(object_tobe_saved) is list:
            store_list_text(object_tobe_saved)


    # Store 'description_sections_top' filtered by 'filter_vocabulary' to 'store_path' in multiple files
    #---------------------------------------------------------------------------------------------------------
    def _store_extracted_granular(self):

        ##_deep_extractor('Знания', 'знание')
        def deep_extractor(criteria):
            
            result = [element
                for element in self.description_elements_all
                    if criteria in element]
            
            return sorted(result, key=len)


        for vocabulary, words in self.filter_vocabulary.items():
            new_store_path = self.store_path + '/' + vocabulary
            os.makedirs(new_store_path, exist_ok=True)
            for criteria in words:
                store_batch = deep_extractor(criteria)
                if store_batch:
                    with open(f"{new_store_path}/{criteria}.txt", 'w', encoding='utf8') as file:
                        file.write("\n".join(sorted(store_batch, key=len)))


#---------------------------------------------------------------------------------------------------------
#---Collectors--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Collect key skills
    #---------------------------------------------------------------------------------------------------------
    def _skills_collector(self):
        
        raw_key_skills = [vacancy.get('key_skills')
            for vacancy in self.vacancies]

        # Cleaning skills
        mixed_key_skills = [key_skill.get('name')
            for item in raw_key_skills
                for key_skill in item]

        # Forms {key_skill : number of entries}
        key_skills_counted = {skill : mixed_key_skills.count(skill)
            for skill in mixed_key_skills}

        # Forms {key_skill : number of entries}
        ##key_skills_counted = {}
        ##for skill in mixed_key_skills:
        ##    key_skills_counted[skill] = key_skills_counted.get(skill, 0) + 1

        # Sort by number of entries
        self.skills_all = sorted(key_skills_counted.items(),
                                 key=lambda x: x[1],
                                 reverse=True)
        
        self.skills = self.skills_all[0:100]


    # Collect required work experience from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _experience_collector(self):

        raw_experience = [full_vacancy.get('experience').get('name')
            for full_vacancy in self.vacancies]
        
        # Forms {experience : number of entries}
        experience = {exp : raw_experience.count(exp)
            for exp in raw_experience}
        
        # Sort by number of entries
        self.experience = sorted(experience.items(),
                                 key=lambda x: x[1],
                                 reverse=True)


    # Collect vacancy names
    #---------------------------------------------------------------------------------------------------------
    def _vacancy_names_collector(self):

        vacancy_names = [vacancy.get('name').lower()
            for vacancy in self.vacancies]
        
        # Forms {vacancy name : number of entries}
        vacancy_names_counted = {name : vacancy_names.count(name)
            for name in vacancy_names}
        
        # Sort by number of entries
        self.vacancy_names = sorted(vacancy_names_counted.items(),
                                    key=lambda x: x[1],
                                    reverse=True)


    # Collect specialization areas from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _prof_areas_collector(self):

        ##raw_area_ids = [categories.get('id')
        ##   for raw_specialization in raw_specializations
        ##      for categories in raw_specialization]
        ##raw_areas = {categories.get('profarea_name') : categories.get('name')
        ##    for raw_specialization in raw_specializations
        ##        for categories in raw_specialization}
        ##Forms {experience : number of entries}
        ##areas = {id : raw_area_ids.count(id)
        ##    for id in raw_area_ids}

        raw_specializations = [full_vacancy.get('specializations')
            for full_vacancy in self.vacancies]
        
        specializations = [vacancy_specializations
            for vacancy_specializations_list in raw_specializations
                for vacancy_specializations in vacancy_specializations_list]
        
        profareas = [key['profarea_name']
            for key in specializations]
        
        profareas_granular = [key['name']
            for key in specializations]
        
        # Forms {profarea : number of entries}
        profareas_counted = {profarea : profareas.count(profarea)
            for profarea in profareas}
        
        # Forms {granular profarea : number of entries}        
        profareas_granular_counted = {profarea : profareas_granular.count(profarea)
            for profarea in profareas_granular}

        # Sort by number of entries
        self.profareas = sorted(profareas_counted.items(),
                                key=lambda x: x[1],
                                reverse=True)

        # Sort by number of entries        
        self.profareas_granular = sorted(profareas_granular_counted.items(),
                                         key=lambda x: x[1],
                                         reverse=True)

    
    # Collect creation dates from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _creation_dates_collector(self):

        raw_create_dates = [vacancy.get('created_at')
            for vacancy in self.vacancies]
        
        # Sort by date of publication
        self.dates = sorted({date : raw_create_dates.count(date)
            for date in raw_create_dates})

    
    # Collect employers
    #---------------------------------------------------------------------------------------------------------
    def _employers_collector(self):

        self.employers_full = [vacancy.get('employer')
            for vacancy in self.vacancies]

        self.employers_brief = {vacancy.get('employer').get('name') : vacancy.get('employer').get('alternate_url')
            for vacancy in self.vacancies}


    # Collect regions
    #---------------------------------------------------------------------------------------------------------
    def _regions_collector(self):

        regions = [vacancy.get('area').get('name')
            for vacancy in self.vacancies]

        # Forms {regions : number of entries}
        regions_counted = {region : regions.count(region)
            for region in regions}
        
        # Sort by number of entries
        self.regions = sorted(regions_counted.items(),
                                    key=lambda x: x[1],
                                    reverse=True)


#---------------------------------------------------------------------------------------------------------
#---Extractors--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Wordbags formed from self.description_sections_top, which in turn is
    # Top of 'strong's' dictionary formed from lots of batches of different vacancies
    #---------------------------------------------------------------------------------------------------------
    def _wordbags_extractor(self):

        def extract_by_criteria(criteria):
            
            if self.description_elements.get(criteria):
                clear_strings = [re.sub("[^А-Яа-я0-9-.\s]", "", describe_string.lower().strip().strip('.'))
                    for describe_string in self.description_elements.get(criteria)]

                unique_clear_set = set(clear_strings)
                unique_strings = [str(string)
                    for string in unique_clear_set]

                ##unique_strings = sorted(unique_strings, key=len)
                bags_words = [collections.Counter(re.findall(r'\w+', string))
                    for string in unique_strings]

                bag_words = sum(bags_words, collections.Counter())
                sorted_bag = sorted(bag_words.items(), key=lambda x: x[1], reverse=True)
                result = [word for word in sorted_bag
                    if len(word[0]) > 4]

                return result
        
        self.wordbags = {criteria : extract_by_criteria(criteria)
            for criteria in self.description_sections_top}
        
        all_words_in_string = ' '.join(self.description_elements_all)    
        bags_words = collections.Counter(re.findall(r'\w+', all_words_in_string))
        self.wordbags_all = sorted(bags_words.items(), key=lambda x: x[1], reverse=True)


    # Extract all english words from vacancy desriptions
    #---------------------------------------------------------------------------------------------------------
    def _keywords_extractor(self):

        # Texts list from vacancy descriptions
        descriptions = [BeautifulSoup(vacancy.get('description'), 'html.parser').get_text()
            for vacancy in self.vacancies]

        # Extract english words
        raw_eng_extraxtions = [re.sub("[^A-Za-z]", " ", description.strip())
            for description in descriptions]
        
        # Clearing
        raw_eng_words = [raw_eng_extraxtion.split('  ')
            for raw_eng_extraxtion in raw_eng_extraxtions]
        
        eng_words = [words.strip()
            for raw_eng_word in raw_eng_words
                for words in raw_eng_word
                    if words != '']
        
        clear_eng_words = list(filter(None, eng_words))
        eng_words_mixed = {word : clear_eng_words.count(word)
            for word in clear_eng_words}

        # Sorted by number of entries
        self.keywords_all = sorted(eng_words_mixed.items(), key=lambda x: x[1], reverse=True)
        self.keywords = self.keywords_all[0:100]


    # Extract child elements from all subject headings (html 'strongs')
    #---------------------------------------------------------------------------------------------------------
    def _description_elements_extractor(self):

        # bs4.BeautifulSoup objects list formed from vacancy descriptions
        vacancy_descriptions = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        p_tags = [p.text.strip().lower()
            for soup in vacancy_descriptions
                for p in soup.find_all('p')]
        li_tags = [li.text.strip().lower()
            for soup in vacancy_descriptions
                for li in soup.find_all('li')]
        
        self.description_elements_all = list(set(p_tags + li_tags))

    
    # Extract multiple different things from vacancy description bodies
    #---------------------------------------------------------------------------------------------------------
    def _description_sections_extractor(self):

        # bs4.BeautifulSoup objects list formed from vacancy descriptions
        description_soups = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        # Vacancy descriptions sections list grouped by vacancy framed into <strong> tags
        strong_soups = [description_soup.findAll('strong')
            for description_soup in description_soups]

        # All vacancy descriptions sections from all vacancies in common list
        strongs = [strong.text
            for strong_soup in strong_soups
                for strong in strong_soup]

        # Clearing
        clear_strongs = [re.sub("[^А-Яа-я\s]", "", strong.strip())
            for strong in strongs]

        clear_strongs = list(filter(None, clear_strongs))
        clear_strongs = list(filter(lambda x: x!=' ', clear_strongs))

        ##self.description_sections = clear_strongs

        # Forms {strong : number of entries}
        strongs_counted = {strong : clear_strongs.count(strong)
            for strong in clear_strongs}

        # Sort by number of entries
        sorted_strongs = sorted(strongs_counted.items(), key=lambda x: x[1], reverse=True)
        
        self.description_sections = sorted([strong[0]
            for strong in sorted_strongs], key=len, reverse=True)
        
        strong_top = [strong[0]
            for strong in sorted_strongs[:10]]

        self.description_elements = {key: []
            for key in strong_top}

        self.description_elements_top = {key: []
            for key in self.description_sections_top}

        for description in description_soups:
            strongs = description.findAll('strong')
            for strong in strongs:
                for top in strong_top:
                    if strong.get_text().count(top):
                    ##if len(strong.findNext().findAll('li')) > 0:
                        try:
                            self.description_elements[top] += [item.text
                                for item in strong.findNext().findAll('li')]
                        except AttributeError:
                            pass
                
                for top in self.description_sections_top:
                    if strong.get_text().count(top):
                    ##if len(strong.findNext().findAll('li')) > 0:
                        try:
                            self.description_elements_top[top] += [item.text
                                for item in strong.findNext().findAll('li')]
                        except AttributeError:
                            pass
        
       
    # Get python list of list 'description_sections_top' filtered by custom 'filter_vocabulary' key
    #---------------------------------------------------------------------------------------------------------
    def _by_word_extractor(self, criteria):
            
        result = [element
            for element in self.description_elements_all
                if criteria in element]
        
        return sorted(result, key=len)


#---------------------------------------------------------------------------------------------------------
#---Misc--------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Remove dubplicates in vacancies list
    #---------------------------------------------------------------------------------------------------------
    def _duplicate_vacancies_remover(self):
        
        unique_vacancies = []

        for vacancy in self.vacancies:
            if vacancy not in unique_vacancies:
                unique_vacancies.append(vacancy)

        self.vacancies = unique_vacancies


    # Count unique vacancies in vacancies list
    #---------------------------------------------------------------------------------------------------------
    def _unique_counter(self):

        self.unique = len({vacancy.get('id')
            for vacancy in self.vacancies})


    # Group salaries into number of clusters
    #---------------------------------------------------------------------------------------------------------
    def _group_by_salary(self):

        def _get_salary_group(salary):
            return {
                salary < 20000: 'Менее 20000',
                20000 <= salary < 30000: '20000-30000',
                30000 <= salary < 40000: '30000-40000',
                40000 <= salary < 50000: '40000-50000',
                50000 <= salary < 60000: '50000-60000',
                60000 <= salary < 70000: '60000-70000',
                70000 <= salary < 90000: '70000-90000',
                90000 <= salary: 'Более 90000'
            }[True]

        for vacancy in self.vacancies:
            if vacancy.get('salary'):
                salary = dict(vacancy['salary'])
                if salary.get('currency') == 'RUR':
                    if salary.get('gross'):
                        if salary.get('from'):
                            salary['from'] = salary['from'] * 0.87
                        if salary.get('to'):
                            salary['to'] = salary['to'] * 0.87
                    if salary.get('from'):
                        self.salary_groups[_get_salary_group(int(salary.get('from')))] += 1
                    if salary.get('to'):
                        self.salary_groups[_get_salary_group(int(salary.get('to')))] += 1


    # Calculate average salary
    #---------------------------------------------------------------------------------------------------------
    def _average_salary(self):

        sum = total = 0
        for vacancy in self.vacancies:
            if vacancy.get('salary'):
                salary = dict(vacancy['salary'])
                if salary.get('currency') == 'RUR':
                    if salary.get('gross'):
                        if salary.get('from'):
                            salary['from'] = salary['from'] * 0.87
                        if salary.get('to'):
                            salary['to'] = salary['to'] * 0.87
                    if salary.get('from'):
                        sum += salary.get('from')
                        total += 1
                    if salary.get('to'):
                        sum += salary.get('to')
                        total += 1
        if total > 0:
            self.average_salary = round(sum/total)


    # Calculate median salary
    #---------------------------------------------------------------------------------------------------------
    def _median_salary(self):

        salary_all = []
        for vacancy in self.vacancies:
            if vacancy.get('salary'):
                salary = dict(vacancy['salary'])
                if salary.get('currency') == 'RUR':
                    if salary.get('gross'):
                        if salary.get('from'):
                            salary['from'] = salary['from'] * 0.87
                        if salary.get('to'):
                            salary['to'] = salary['to'] * 0.87
                    if salary.get('from'):
                        salary_all.append(salary.get('from'))
                    if salary.get('to'):
                        salary_all.append(salary.get('to'))

        self.median_salary = statistics.median(salary_all)


    # Calculate modal salary
    #---------------------------------------------------------------------------------------------------------
    def _modal_salary(self):
        
        for group, salary in self.salary_groups.items():
            if salary == max(self.salary_groups.values()):
                self.modal_salary = group


#---------------------------------------------------------------------------------------------------------
#---Analyze-----------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Call all analyze methods                        
    def analyze(self):

        # If class instance doesn't contains actual vacancies
        if self.__initial: self._retrievement_confirmator()
        ##if self.__initial: self.vacancies_retriever()

        self._duplicate_vacancies_remover()
        self._skills_collector()
        self._experience_collector()
        self._prof_areas_collector()
        self._creation_dates_collector()
        self._vacancy_names_collector()
        self._regions_collector()
        self._keywords_extractor()
        self._description_elements_extractor()
        self._description_sections_extractor()
        self._wordbags_extractor()
        self._unique_counter()
        self._group_by_salary()
        self._average_salary()
        self._median_salary()
        self._modal_salary()
        self._employers_collector()
