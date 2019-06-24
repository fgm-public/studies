import vh
import cProfile

def profiler():
    v = vh.VacancyHandler('Системный аналитик')
    v.unpickle_vacancies("path/to/vacancies_batch.pickle")
    v.analyze()

cProfile.run('profiler()')