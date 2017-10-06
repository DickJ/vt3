import logging
from multiprocessing import Process
from worker.online_schedule import run_online_schedule
from worker.update_confirmation_codes import run_conf_code_update

if __name__ == '__main__':
    logging.info("Worker Starting")
    processes = [Process(target=run_online_schedule),
                 Process(target=run_conf_code_update)]

    for i in processes:
        i.start()
    for i in processes:
        i.join()

    logging.info("All threads joined. Worker exiting.")