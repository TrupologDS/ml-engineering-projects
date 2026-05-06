"""
Load-test script for /api/price/.
Usage:
  python3 scripts/load.py --url http://localhost:4648/api/price/ --total 500 --concurrency 20
"""

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_payload(uid: int) -> bytes:
    build_year = 1950 + random.randint(0, 74)
    btype = 1 + random.randint(0, 2)
    flats = 50 + random.randint(0, 199)
    floors_total = 5 + random.randint(0, 19)
    floor = 1 + random.randint(0, 19)
    karea = 6 + random.randint(0, 19)
    larea = 15 + random.randint(0, 59)
    rooms = 1 + random.randint(0, 3)
    has_elev = random.randint(0, 1)
    is_ap = random.randint(0, 1)
    studio = random.randint(0, 1)
    total_area = 40 + random.randint(0, 79)

    payload = {
        "user_id": str(uid),
        "model_params": {
            "build_year": build_year,
            "building_type_int": btype,
            "latitude": 55.751244,
            "longitude": 37.618423,
            "ceiling_height": 3,
            "flats_count": flats,
            "floors_total": floors_total,
            "has_elevator": has_elev,
            "floor": floor,
            "kitchen_area": karea,
            "living_area": larea,
            "rooms": rooms,
            "is_apartment": is_ap,
            "studio": studio,
            "total_area": total_area,
        },
    }
    return json.dumps(payload).encode("utf-8")


def send(url: str, uid: int, timeout: float = 5.0) -> int:
    data = build_payload(uid)
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status
    except HTTPError as e:
        return e.code
    except URLError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:4648/api/price/", help="Endpoint URL")
    ap.add_argument("--total", type=int, default=200, help="Total requests")
    ap.add_argument("--concurrency", type=int, default=10, help="Parallel threads")
    ap.add_argument("--timeout", type=float, default=5.0, help="Per-request timeout (s)")
    args = ap.parse_args()

    start = time.time()
    ok = err = 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        jobs = executor.map(
            lambda uid: send(args.url, uid, args.timeout),
            range(1, args.total + 1),
        )
        for status in jobs:
            if 200 <= status < 300:
                ok += 1
            else:
                err += 1

    dur = time.time() - start
    rps = args.total / dur if dur > 0 else 0
    print(f"done. total={args.total}, ok={ok}, err={err}, time={dur:.2f}s, ~RPS={rps:.1f}")


if __name__ == "__main__":
    main()
