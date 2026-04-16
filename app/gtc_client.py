"""
GoTimeCloud API Client - Async, with UTC support and rich daily summary.
"""
import hashlib
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class GTCClient:
    def __init__(self, base_url: str, company: str, username: str, password: str, utc: int = 2):
        self.base_url = base_url.rstrip("/") + "/api/v1"
        self.company = company
        self._username = username
        self._password = password
        self.utc = utc
        self.token = None
        self._client = httpx.AsyncClient(timeout=15)

    def _headers(self) -> dict:
        now = datetime.utcnow()
        h = {
            "DATE": now.strftime("%Y%m%d"),
            "TIME": now.strftime("%H%M%S"),
            "UTC": f"+{self.utc}",
            "Content-Type": "application/json",
        }
        if self.token:
            h["X-Token"] = self.token
        return h

    async def _call(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        resp = await self._client.request(method, url, headers=self._headers(), **kwargs)
        return resp.json()

    # ── Auth ──────────────────────────────────────

    async def connect(self) -> bool:
        r = await self._call("POST", "/login", json={
            "company": self.company,
            "username": hashlib.sha256(self._username.encode()).hexdigest(),
            "password": hashlib.sha256(self._password.encode()).hexdigest(),
        })
        if r["status"]["code"] == 200:
            self.token = r["data"]["token"]
            return True
        raise ConnectionError(f"GTC login failed: {r['status']['message']}")

    # ── Employees ─────────────────────────────────

    async def list_employees(self, limit: int = 100) -> list:
        r = await self._call("GET", "/employees", params={"limit": limit})
        return r["data"]

    async def get_employee(self, code: str) -> dict:
        r = await self._call("GET", f"/employees/{code}")
        return r["data"]

    async def find_employee(self, name: str = None, nif: str = None) -> Optional[dict]:
        employees = await self.list_employees()
        for e in employees:
            full = f"{e.get('name', '')} {e.get('surnames', '')}".lower()
            if name and name.lower() in full:
                return e
            if nif and nif.upper() == e.get("nif", "").upper():
                return e
        return None

    async def create_employee(self, code: str, name: str, surnames: str, **kwargs) -> dict:
        payload = {
            "name": name, "surnames": surnames,
            "department": kwargs.get("department", "00000"),
            "center": kwargs.get("center", "00000"),
            "workday": kwargs.get("workday", "0000"),
            "calendar": kwargs.get("calendar", "000000000"),
            "profile": kwargs.get("profile", "000000000"),
            "active": kwargs.get("active", True),
        }
        for f in ["nif", "mail", "telephone", "birthdate", "address", "town", "county", "cp", "supervisor"]:
            if f in kwargs:
                payload[f] = kwargs[f]
        return await self._call("POST", f"/employees/{code}", json=payload)

    async def update_employee(self, code: str, **kwargs) -> dict:
        return await self._call("PUT", f"/employees/{code}", json=kwargs)

    async def delete_employee(self, code: str) -> dict:
        return await self._call("DELETE", f"/employees/{code}")

    # ── Punches ───────────────────────────────────

    async def list_punches(self, date_from: str, date_to: str, limit: int = 100) -> list:
        r = await self._call("GET", "/punches",
                             params={"dateFrom": date_from, "dateTo": date_to, "limit": limit})
        return r["data"]

    async def get_employee_punches(self, code: str, date_from: str, date_to: str) -> list:
        r = await self._call("GET", f"/punches/{code}",
                             params={"dateFrom": date_from, "dateTo": date_to})
        return r["data"]

    async def get_today_punches(self, code: str) -> list:
        today = datetime.now().strftime("%Y%m%d")
        return await self.get_employee_punches(code, today, today)

    async def get_latest_punches(self, date: str = None) -> list:
        params = {"date": date} if date else {}
        r = await self._call("GET", "/punches/latest", params=params)
        return r["data"]

    async def register_punch(self, employee_code: str, date: str, time: str) -> dict:
        return await self._call("POST", "/punches", json={
            "values": [{"employee": employee_code, "date": date, "time": time,
                        "utc": self.utc, "event": "0000"}]
        })

    async def register_punch_now(self, employee_code: str) -> dict:
        now = datetime.utcnow() + timedelta(hours=self.utc)
        return await self.register_punch(employee_code, now.strftime("%Y%m%d"), now.strftime("%H%M%S"))

    # ── Status / Petitions ────────────────────────

    async def set_employee_status(self, code: str, date: str, event: str, value: int = 0) -> dict:
        return await self._call("POST", f"/employees/{code}/status/{date}",
                                json={"event": event, "value": value})

    async def list_petitions(self, date_from: str, date_to: str, limit: int = 50) -> list:
        r = await self._call("GET", "/petitions",
                             params={"dateFrom": date_from, "dateTo": date_to, "limit": limit})
        return r["data"]

    async def create_petition(self, employee_code: str, event: str,
                              date: str, date_to: str = None) -> dict:
        lines = [{"date": date, "event": event}]
        if date_to:
            lines[0]["dateTo"] = date_to
        return await self._call("POST", "/petitions", json={
            "employee": employee_code, "family": 0, "subfamily": 0, "action": 0,
            "lines": json.dumps(lines),
        })

    # ── Accruals ──────────────────────────────────

    async def get_accruals(self, code: str, year: str = None) -> list:
        year = year or str(datetime.now().year)
        r = await self._call("GET", f"/accruals/{code}", params={"year": year})
        return r["data"]

    # ── Config ────────────────────────────────────

    async def list_workdays(self) -> list:
        r = await self._call("GET", "/workdays")
        return r["data"]

    async def get_workday(self, code: str) -> dict:
        r = await self._call("GET", f"/workdays/{code}")
        return r["data"]

    async def list_profiles(self) -> list:
        r = await self._call("GET", "/profiles")
        return r["data"]

    async def list_calendars(self, year: str = None) -> list:
        year = year or str(datetime.now().year)
        r = await self._call("GET", "/calendars", params={"year": year})
        return r["data"]

    async def list_centers(self) -> list:
        r = await self._call("GET", "/centers")
        return r["data"]

    async def list_departments(self) -> list:
        r = await self._call("GET", "/departments")
        return r["data"]

    async def list_devices(self) -> list:
        r = await self._call("GET", "/devices")
        return r["data"]

    async def get_device_status(self) -> list:
        r = await self._call("GET", "/devices/status")
        return r["data"]

    async def list_events(self) -> list:
        r = await self._call("GET", "/events")
        return r["data"]

    async def get_subscription(self) -> dict:
        r = await self._call("GET", "/subscription")
        return r["data"]

    # ── Rich daily summary (from whatsapp-bot) ────

    async def daily_summary(self, date: str = None) -> dict:
        date = date or datetime.now().strftime("%Y%m%d")
        employees = await self.list_employees()
        missing = []
        late = []
        early = []
        punches_count = 0
        for emp in employees:
            if not emp.get("active", True):
                continue
            punches = await self.get_employee_punches(emp["code"], date, date)
            name = f"{emp['name']} {emp.get('surnames', '')}"
            if punches:
                punches_count += 1
            if len(punches) % 2 != 0:
                missing.append({
                    "name": name, "code": emp["code"],
                    "punches": len(punches),
                    "last_punch": punches[-1].get("time", "?") if punches else "none",
                })
            if len(punches) >= 2:
                try:
                    wd = await self.get_workday(emp.get("workday", ""))
                    s1 = wd.get("firstSession", {}).get("start", "")
                    s2 = wd.get("secondSession", {}).get("end", "")
                    if s1 and punches[0].get("time"):
                        diff = (int(punches[0]["time"][:2]) * 60 + int(punches[0]["time"][2:4])) - \
                               (int(s1[:2]) * 60 + int(s1[2:4]))
                        if diff > 15:
                            late.append({"name": name, "expected": s1, "actual": punches[0]["time"], "delay_min": diff})
                    if s2 and punches[-1].get("time"):
                        diff = (int(s2[:2]) * 60 + int(s2[2:4])) - \
                               (int(punches[-1]["time"][:2]) * 60 + int(punches[-1]["time"][2:4]))
                        if diff > 15:
                            early.append({"name": name, "expected": s2, "actual": punches[-1]["time"], "left_early_min": diff})
                except Exception:
                    pass
        devices_status = await self.get_device_status()
        offline = [d for d in devices_status if not d.get("isConnected", True)]
        return {
            "date": date, "total_employees": len(employees),
            "employees_with_punches": punches_count,
            "missing_exit_punch": missing, "late_arrivals": late,
            "early_departures": early, "offline_devices": offline,
        }

    async def check_missing_punches(self, date: str = None) -> list:
        date = date or datetime.now().strftime("%Y%m%d")
        employees = await self.list_employees()
        result = []
        for emp in employees:
            if not emp.get("active", True):
                continue
            punches = await self.get_employee_punches(emp["code"], date, date)
            if len(punches) % 2 != 0:
                result.append({
                    "code": emp["code"],
                    "name": f"{emp['name']} {emp.get('surnames', '')}",
                    "punches": len(punches),
                    "last_punch": punches[-1].get("time", "?") if punches else "none",
                })
        return result
