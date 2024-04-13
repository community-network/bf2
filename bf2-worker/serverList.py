"""Get server lists from games and insert them into the database."""

import os
import asyncio
from threading import Thread
from subprocess import run, TimeoutExpired
from pymongo.mongo_client import MongoClient
from quart import Quart
from hypercorn.config import Config
from hypercorn.asyncio import serve

while_is_running = True


def ealist_gather(main_db: MongoClient, arguments: str, filename: str, end_name: str):
    """Run ealist with arguments and insert the servers into the database."""
    try:
        try:
            _ = run(
                [
                    "wineconsole",
                    "--backend=curses",
                    "./ealist/ealist.exe",
                    "-a",
                    os.environ.get("EALIST_USER", ""),
                    os.environ.get("EALIST_PASS", ""),
                    *arguments.split(),
                ],
                timeout=15,
                check=True,
            )
        except TimeoutExpired:
            print(f"Timeout for {end_name} (15s) expired")

        file = open(f"./{filename}", "r", encoding="utf-8")
        raw_server_list = file.read().split("\n")
        file.close()
        server_lister(main_db, raw_server_list, end_name)
    except Exception as e:
        print(f"ealist_gather {e}")


def gslist_gather(main_db: MongoClient, arguments: str, end_name: str):
    """Run gslist-2 with arguments and insert the servers into the database."""
    try:
        result = run(
            ["./gslist-2", *arguments.split()],
            capture_output=True,
            encoding="utf8",
            timeout=15,
            check=True,
        )
        server_lister(main_db, result.stdout.split("\n"), end_name)
    except TimeoutExpired:
        print(f"Timeout for {end_name} (15s) expired")
    except Exception as e:
        print(f"gslist_gather for {end_name}: {e}")


def server_lister(main_db: MongoClient, raw_server_list, end_name: str):
    """List servers from raw_server_list and insert them into the database."""
    found_servers = []
    server_list = []
    for line in raw_server_list:
        server = {}
        key_value_pairs = line.split("\\")
        if len(key_value_pairs) > 1:
            if key_value_pairs[0] not in found_servers:
                for i, _ in enumerate(key_value_pairs):
                    if i % 2 == 1:
                        server[key_value_pairs[i]] = key_value_pairs[i + 1]
                server["serverIp"] = key_value_pairs[0].split(":")[0].strip()
                server["serverPort"] = key_value_pairs[0].split(":")[1].strip()
                found_servers.append(key_value_pairs[0])
                server_list.append(server)
    # Insert or update server list
    gamestats = main_db["gamestats"]
    gamestats["oldGamesServerList"].update_one(
        {"_id": end_name}, {"$set": {"serverList": server_list}}, upsert=True
    )


async def main_loop(main_db: MongoClient):
    """Main loop."""
    while True:
        gslist_gather(
            main_db,
            "-n battlefield2 -x 92.51.181.102 -Y battlefield2 hW6m9a -Q 8 -q",
            "bf2-bf2hub",
        )
        gslist_gather(
            main_db,
            "-n battlefield2 -x master.playbf2.ru -Y battlefield2 hW6m9a -Q 8 -q",
            "bf2-playbf2",
        )
        gslist_gather(
            main_db,
            "-n stella -x stella.ms5.openspy.net:28910 -Q 8 -q",
            "bf2142-openspy",
        )
        gslist_gather(
            main_db,
            "-n stella -x stella.ms.play2142.ru:28910 -Q 8 -q",
            "bf2142-play2142",
        )
        gslist_gather(
            main_db,
            "-n bfield1942 -x master.bf1942.org:28900 -Y bfield1942 HpWx9z -t 2 -Q 0 -q",
            "bfield1942-bf1942org",
        )
        gslist_gather(
            main_db,
            "-n bfvietnam -x master.openspy.net:28900 -Y bfvietnam h2P9dJ -t 2 -Q 0 -q",
            "bfvietnam-openspy",
        )
        gslist_gather(
            main_db,
            "-n bfvietnam -x master2.qtracker.com:28900 -Y bfvietnam h2P9dJ -t 2 -Q 0 -q",
            "bfvietnam-qtracker",
        )
        # ealist_gather(
        #     main_db,
        #     "mohair-pc -n bfbc2-pc-server -X none -o 1",
        #     "bfbc2-pc-server.gsl",
        #     "bfbc2",
        # )
        await asyncio.sleep(10)  # 10 seconds


def start_background_getter():
    """Start the background task."""
    main_db = MongoClient(
        os.environ.get("DB_URL", "")
    )
    asyncio.run(main_loop(main_db))
    global while_is_running
    while_is_running = False


app = Quart(__name__)


@app.before_serving
async def run_on_start():
    """Start a background task on Quart startup."""
    thread = Thread(target=start_background_getter)
    thread.start()


@app.route("/")
def health_check():
    """Health check endpoint."""
    global while_is_running
    if while_is_running:
        return {"status": "ok"}
    else:
        return {"status": "failed"}, 500


if __name__ == "__main__":
    config = Config.from_mapping(
        bind="0.0.0.0:80",
        statsd_host="0.0.0.0:80",
    )
    asyncio.run(serve(app, config))
