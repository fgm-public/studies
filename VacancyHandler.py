import os
import re
import json
import pickle
import pymongo
import requests
import collections
from tqdm import tqdm
from bs4 import BeautifulSoup
#from pymongo import MongoClient


class VacancyHandler:

#---------------------------------------------------------------------------------------------------------
#---Initializations---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Base HeadHunter API-url for vacancy retrievement
    api_url = 'https://api.hh.ru/vacancies'

    #Azure CosmoDB db connection string
    mongo_credentials = ('mongodb://1b145613-0ee0-4-231-b9ee:7w3yd'
                         'n0e2aNuqOTCqxa99hHwJcF4kPrkAmEKFtiDHaR1u'
                         'LOca0u25CcEASZnKk1YJHnqfEs1JyPrHe4gEAFkg'
                         'g==@1b145613-0ee0-4-231-b9ee.documents.a'
                         'zure.com:10255/?ssl=true&replicaSet=glob'
                         'aldb')

    #Select certain 'hh_vacancies' db in mongo
    #mongo_client = pymongo.MongoClient(mongo_credentials)
    #mongo_db = mongo_client.hh_vacancies
    mongo_db = pymongo.MongoClient(mongo_credentials).hh_vacancies


    def __init__(self, search_criteria, average_salary=200000, search_field='name'):
        
        #Global path to store pickles and results
        self.store_path = 'D:/store'

        #Vacancy search_criteria. Occupation name, in main
        self.search_criteria = search_criteria
        
        #Full vacancies itself
        self.vacancies = []

        #Keyskills top and all
        self.skills = None
        self.skills_all = None
 
        #Keywords (all english words) top and all
        self.keywords = None
        self.keywords_all = None

        #All subject headings (html 'strongs') from vacancy descriptions
        self.description_sections = None

        #Child elements from all subject headings (html 'strongs')
        self.description_elements = None

        #Child elements from top 10 subject headings (html 'strongs')
        self.description_elements_top = None

        #Wordbags formed from self.description_sections_top
        self.wordbags = None
        
        #Professional areas
        self.areas = None
        
        #Publication dates
        self.dates = None
        
        #Required experience
        self.experience = None
        
        #Number of unique vacancies among all
        self.unique = None
        
        #HH clusters
        self.clusters = None

        #Top of 'strong's' dictionary formed from lots of batches of different vacancies
        self.description_sections_top = [
            'Требования',
            'Обязанности',
            'Условия',
            'Мы предлагаем',
        ]

        self.filter_vocabulary = {
            'Знания': ['знание', 'умение', 'навыки',],
            'Администратор': ['информирование', 'корпоративность', 'влияние и воздействие', 'ориентация на стандарт', 'концептуальность мышления', 'организованность стресс менеджмент',],
            'Интегратор': ['честность', 'командная работа', 'коммуникабельность', 'командное лидерство', 'установление контактов', 'управление конфликтами', 'разделение ответственности', 'организаторские способности',],
            'Предприниматель': ['гибкость', 'адаптируемость', 'принятие решения', 'управление рисками', 'инновационное мышление', 'управление изменениями', 'клиенториентированность', 'стратегическое мышление', 'предпринимательский подход',],
            'Производитель': ['активность', 'целеустремленность','последовательность', 'уверенность в себе', 'установка на обучение', 'понимание организации', 'аналитическое мышление', 'ориентация на результат', 'энергетический потенциал', 'профессиональная ответственность',],
            'Тренды': ['hi-po', 'agile', 'digital', 'эмпатия', 'коучинг', 'лидерство', 'коллаборация', 'осознанное влияние', 'креативность мышления', 'эмоциональный интеллект', 'управление эффективностью',],
        }

        #Search and request to API parameters
        self.search_parameters = {
            'text': self.search_criteria,
            'salary': average_salary,
            'per_page': 100,
            'page': 0,
            'clusters': 'true',
            'describe_arguments': 'true',
            }
        
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

    #Retrieve vacancies from hh
    def _vacancies_retriever(self):

        brief_vacancies = []
        current_page = 0
        pages_count = current_page + 1

        while current_page < pages_count:
            self.search_parameters['page'] = current_page
            raw_response = requests.get(VacancyHandler.api_url, params = self.search_parameters)
            response = raw_response.json()
            brief_vacancies += response.get('items')
            pages_count = response.get('pages')
            current_page += 1

        self.clusters = response.get('clusters')

        #Collecting urls which link to full vacancy descriptions
        urls = [vacancy.get('url') for vacancy in brief_vacancies]

        #Form a list of full vacancies
        self.vacancies = [requests.get(url).json() for url in tqdm(urls)]

        #Now the class instance already contains actual vacancies
        self.__initial = False


    #Announces general information on the response to the request
    #Asks for confirmation for the full retrievement
    #Start full retrievement if confirmed
    def _retrievement_confirmator(self):

        raw_response = requests.get(VacancyHandler.api_url, params = self.search_parameters)
        response = raw_response.json()
        pages_count = response.get('pages')
        
        print(f"\nThere are {pages_count*self.search_parameters['per_page']} vacancies",
              f"on '{self.search_parameters.get('text')}' occupation available on hh.ru",
              f"\n\nRetrieve it now ([Y]es, [N]o) ?")
        
        answer = input()

        if answer == 'y':
            print(f"\n\n")
            self._vacancies_retriever()

#---------------------------------------------------------------------------------------------------------
#---Store-------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Store object 'vacancies' into file located in 'store_path' path
    def pickle_vacancies(self):
        with open(f"{self.store_path}/{self.search_parameters.get('text')}.pickle", 'wb') as file:
            pickle.dump(self.vacancies, file)


    #Restore object 'vacancies' from file located in 'store_path' path
    def unpickle_vacancies(self, store_path):
        with open(store_path, 'rb') as file:
            self.vacancies += pickle.load(file)
        
        #Now the class instance already contains actual vacancies
        self.__initial = False


    #Stores vacancies to mongodb
    def store_to_mongo(self):

        #Create collection with vacancies occupation name stored in 'search_criteria'
        collection = VacancyHandler.mongo_db[self.search_criteria]
        #Stores insert results in variable
        insert_result = collection.insert_many(self.vacancies)
        #cursor = collection.find({'salary.from': {'$gt': 30000}})

#---------------------------------------------------------------------------------------------------------
#---Results---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Store custom properties (skills, keywords, etc) into text files located in 'store_path' path
    def store_results_to_files(self):

        self._store_results_text(self.skills_all, 'Навыки')
        self._store_results_text(self.keywords_all, 'Слова')
        self._store_results_text(self.experience, 'Опыт')
        self._store_results_text(self.description_elements_top, 'Категории (Топ)', sort=True)
        self._store_results_text(self.wordbags, 'Мешки слов')
        self._store_extracted_granular()


    #Store arbitrary result stuff into text files located in 'store_path' path
    def _store_results_text(self, object_tobe_saved, filename, sort=False):

        def store_dict_text(dict_tobe_saved):
            #Files will be named after dict keys
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


    #Store 'description_sections_top' filtered by 'filter_vocabulary' to 'store_path' in multiple files
    def _store_extracted_granular(self):

        #_deep_extractor('Знания', 'знание')
        def deep_extractor(criteria):
            
            result = [element
                for element in self.description_elements
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

    #Collect key skills
    def _skills_collector(self):
        
        raw_key_skills = [vacancy.get('key_skills')
            for vacancy in self.vacancies]

        #Cleaning skills
        mixed_key_skills = [key_skill.get('name')
            for item in raw_key_skills
                for key_skill in item]

        #Forms {key_skill : number of entries}
        ks_entries_count_by_name = {skill : mixed_key_skills.count(skill)
            for skill in mixed_key_skills}

        #Sort by number of entries
        self.skills_all = sorted(ks_entries_count_by_name.items(), key=lambda x: x[1], reverse=True)
        self.skills = self.skills_all[0:100]


    #Collect required work experience from vacancies
    def _experience_collector(self):

        raw_experience = [full_vacancy.get('experience').get('name')
            for full_vacancy in self.vacancies]
        
        #Forms {experience : number of entries}
        experience = {exp : raw_experience.count(exp)
            for exp in raw_experience}

        self.experience = sorted(experience.items(), key=lambda x: x[1], reverse=True)


    #Collect specialization areas from vacancies
    def _areas_collector(self):

        raw_specializations = [full_vacancy.get('specializations')
            for full_vacancy in self.vacancies]

        raw_area_ids = [categories.get('id')
            for raw_specialization in raw_specializations
                for categories in raw_specialization]
        
        #Forms {experience : number of entries}
        areas = {id : raw_area_ids.count(id)
            for id in raw_area_ids}

        self.areas = sorted(areas.items(), key=lambda x: x[1], reverse=True)

    
    #Collect creation dates from vacancies
    def _creation_dates_collector(self):

        raw_create_dates = [vacancy.get('created_at')
            for vacancy in self.vacancies]

        self.dates = sorted({date : raw_create_dates.count(date)
            for date in raw_create_dates})

#---------------------------------------------------------------------------------------------------------
#---Extractors--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Wordbags formed from self.description_sections_top, which in turn is
    #Top of 'strong's' dictionary formed from lots of batches of different vacancies
    def _wordbags_extractor(self):

        def extract_by_criteria(criteria):
            clear_strings = [re.sub("[^А-Яа-я0-9-.\s]", "", describe_string.lower().strip().strip('.'))
                for describe_string in self.description_elements_top.get(criteria)]

            unique_clear_set = set(clear_strings)
            unique_strings = [str(string)
                for string in unique_clear_set]

            #unique_strings = sorted(unique_strings, key=len)
            bags_words = [collections.Counter(re.findall(r'\w+', string))
                for string in unique_strings]

            bag_words = sum(bags_words, collections.Counter())
            sorted_bag = sorted(bag_words.items(), key=lambda x: x[1], reverse=True)
            result = [word for word in sorted_bag
                if len(word[0]) > 4]

            return result
        
        self.wordbags = {criteria : extract_by_criteria(criteria)
            for criteria in self.description_sections_top}


    #Extract all english words from vacancy desriptions
    def _keywords_extractor(self):

        descriptions = [BeautifulSoup(vacancy.get('description'), 'html.parser').get_text()
            for vacancy in self.vacancies]
        
        raw_eng_extraxtions = [re.sub("[^A-Za-z]", " ", description.strip())
            for description in descriptions]
        
        raw_eng_words = [raw_eng_extraxtion.split('  ')
            for raw_eng_extraxtion in raw_eng_extraxtions]
        
        eng_words = [words.strip()
            for raw_eng_word in raw_eng_words
                for words in raw_eng_word
                    if words != '']
        
        clear_eng_words = list(filter(None, eng_words))
        eng_words_mixed = {word : clear_eng_words.count(word)
            for word in clear_eng_words}

        #Sorted by number of entries
        self.keywords_all = sorted(eng_words_mixed.items(), key=lambda x: x[1], reverse=True)
        self.keywords = self.keywords_all[0:100]


    #Extract child elements from all subject headings (html 'strongs')
    def _description_elements_extractor(self):

        soups = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        ps = [p.text.strip().lower()
            for soup in soups
                for p in soup.find_all('p')]
        lis = [li.text.strip().lower()
            for soup in soups
                for li in soup.find_all('li')]
        
        self.description_elements = list(set(ps + lis))


    def _description_sections_extractor(self):

        description_soups = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        strong_soups = [description_soup.findAll('strong')
            for description_soup in description_soups]
        strongs = [strong.text
            for strong_soup in strong_soups
                for strong in strong_soup]

        clear_strongs = [re.sub("[^А-Яа-я\s]", "", strong.strip())
            for strong in strongs]
        clear_strongs = list(filter(None, clear_strongs))
        clear_strongs = list(filter(lambda x: x!=' ', clear_strongs))

        #self.description_sections = clear_strongs

        strongs_rating = {strong : clear_strongs.count(strong)
            for strong in clear_strongs}
        
        sorted_strongs = sorted(strongs_rating.items(), key=lambda x: x[1], reverse=True)
        
        self.description_sections = sorted([strong[0]
            for strong in sorted_strongs], key=len, reverse=True)
        
        strong_top = [strong[0]
            for strong in sorted_strongs[:10]]

        self.description_elements_top = {key: []
            for key in strong_top}
        
        for description in description_soups:
        
            strongs = description.findAll('strong')
        
            for strong in strongs:
                for top in strong_top:
        
                    if strong.get_text().count(top):
                    #if len(strong.findNext().findAll('li')) > 0:
                        try:
                            self.description_elements_top[top] += [item.text
                                for item in strong.findNext().findAll('li')]
                        except AttributeError:
                            pass

#---------------------------------------------------------------------------------------------------------
#---Misc--------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Remove dubplicates in vacancies list
    def _duplicate_vacancies_remover(self):
        
        unique_vacancies = []

        for vacancy in self.vacancies:
            if vacancy not in unique_vacancies:
                unique_vacancies.append(vacancy)

        self.vacancies = unique_vacancies


    #Count unique vacancies in vacancies list
    def _unique_counter(self):
        self.unique = len({vacancy.get('id')
            for vacancy in self.vacancies})

#---------------------------------------------------------------------------------------------------------
#---Analyze-----------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    #Call all analyze methods                        
    def analyze(self):
        #If class instance doesn't contains actual vacancies
        if self.__initial: self._retrievement_confirmator()
        #if self.__initial: self.vacancies_retriever()
        self._duplicate_vacancies_remover()
        self._skills_collector()
        self._experience_collector()
        self._areas_collector()
        self._creation_dates_collector()
        self._keywords_extractor()
        self._description_elements_extractor()
        self._description_sections_extractor()
        self._wordbags_extractor()
        self._unique_counter()
