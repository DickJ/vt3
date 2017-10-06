import logging
from utils.u_db import get_db_conn_and_cursor


def run_conf_code_update():
    """
    Deletes confirmation codes older than 24 hours
    """
    logging.info({'func': 'run_conf_code_update', 'msg': 'starting'})

    conn, cur = get_db_conn_and_cursor()
    cur.execute("DELETE FROM unverified WHERE current_timestamp - datetime > '24 hours';")
    conn.commit()
    cur.close()
    conn.close()

    logging.info({'func': 'run_conf_code_update', 'msg': 'returning'})