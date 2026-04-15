"""
GoTimeCloud API Client - Lightweight version for the chatbot
"""
import hashlib
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional


class GTCClient:
    def __init__(self, base_url: str, company: str, username: str, password: str):
        self.base_url = base_url.rstrip("/") + "/api/v1"
        self.company = company
        self._username = username
        self._password = password
        self.token = None

    def _headers(self) -> dict:
        now = datetime.utcnow()
        h = {"DATE": now.strftime("%Y%m%d"), "TIME": now.strftime("%H%M%S"), "UTC": "+0", "Content-Type": "application/json"}
        if self.token:
            h["X-Token"] = self.token
        return h

    async def connect(self) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base_url}/login", json={
                "company": self.company,
                "username": hashlib.sha256(self._username.encode()).hexdigest(),
                "password": hashlib.sha256(self._password.encode()).hexdigest(),
            }, headers=self._headers())
            r = resp.json()
            if r["status"]["code"] == 200:
                self.token = r["data"]["token"]
                return True
            raise ConnectionError(f"GTC login failed: {r['status']['message']}")

    async def _call(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(method, f"{self.base_url}{path}", headers=self._headers(), **kwargs)
            return resp.json()

    # ── Employees ────────────────────────────────

    async def list_employees(self, limit: int = 100) -> list:
        r = await self._call("GET", "/employees", params={"limit": limit})
        return r["data"]

    async def get_employee(self, code: str) -> dict:
        r = await self._call("GET", f"/employees/{code}")
        return r["data"]

    async def find_employee(self, name: str = None, nif: str = None) -> Optional[dict]:
        employees = await self.list_employees()
        for e in employees:
            if name and name.lower() in f"{e.get('name','')} {e.get('surnames','')}".lower():
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
        }
        for f in ["nif", "mail", "telephone", "birthdate", "address", "town", "county", "cp", "supervisor"]:
            if f in kwargs:
                payload[f] = kwargs[f]
        return await self._call("POST", f"/employees/{code}", json=payload)

    async def update_employee(self, code: str, **kwargs) -> dict:
        return await self._call("PUT", f"/employees/{code}", json=kwargs)

    async def delete_employee(self, code: str) -> dict:
        return await self._call("DELETE", f"/employees/{code}")

    # ── Punches ──────────────────────────────────

    async def list_punches(self, date_from: str, date_to: str, limit: int = 100) -> list:
        r = await self._call("GET", "/punches", params={"dateFrom": date_from, "dateTo": date_to, "limit": limit})
        return r["data"]

    async def get_employee_punches(self, code: str, date_from: str, date_to: str) -> list:
        r = await self._call("GET", f"/punches/{code}", params={"dateFrom": date_from, "dateTo": date_to})
        return r["data"]

    async def get_latest_punches(self, date: str = None) -> list:
        r = await self._call("GET", "/punches/latest", params={"date": date} if date else {})
        return r["data"]

    async def register_punch(self, employee_code: str, date: str, time: str, utc: int = 2) -> dict:
        return await self._call("POST", "/punches", json={
            "values": [{"employee": employee_code, "date": date, "time": time, "utc": utc, "event": "0000"}]
        })

    async def register_punch_now(self, employee_code: str, utc: int = 2) -> dict:
        now = datetime.utcnow() + timedelta(hours=utc)
        return await self.register_punch(employee_code, now.strftime("%Y%m%d"), now.strftime("%H%M%S"), utc)

    # ── Accruals / Petitions / Config ────────────

    async def get_accruals(self, code: str, year: str = None) -> list:
        year = year or str(datetime.now().year)
        r = await self._call("GET", f"/accruals/{code}", params={"year": year})
        return r["data"]

    async def list_petitions(self, date_from: str, date_to: str) -> list:
        r = await self._call("GET", "/petitions", params={"dateFrom": date_from, "dateTo": date_to})
        return r["data"]

    async def create_petition(self, employee_code: str, event: str, date: str, date_to: str = None) -> dict:
        lines = [{"date": date, "event": event}]
        if date_to:
            lines[0]["dateTo"] = date_to
        return await self._call("POST", "/petitions", json={
            "employee": employee_code, "family": 0, "subfamily": 0, "action": 0,
            "lines": json.dumps(lines),
        })

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

    async def list_devices(self) -> list:
        r = await self._call("GET", "/devices")
        return r["data"]

    async def get_device_status(self) -> list:
        r = await self._call("GET", "/devices/status")
        return r["data"]

    async def list_centers(self) -> list:
        r = await self._call("GET", "/centers")
        return r["data"]

    async def list_departments(self) -> list:
        r = await self._call("GET", "/departments")
        return r["data"]

    async def list_events(self) -> list:
        r = await self._call("GET", "/events")
        return r["data"]

    async def get_subscription(self) -> dict:
        r = await self._call("GET", "/subscription")
        return r["data"]

    # ── Assistant Helpers ────────────────────────

    async def get_today_punches(self, code: str) -> list:
        today = datetime.now().strftime("%Y%m%d")
        return await self.get_employee_punches(code, today, today)

    async def daily_summary(self, date: str = None) -> dict:
        date = date or datetime.now().strftime("%Y%m%d")
        employees = await self.list_employees()
        missing = []
        late = []
        early = []
        for emp in employees:
            if not emp.get("active", True):
                continue
            punches = await self.get_employee_punches(emp["code"], date, date)
            name = f"{emp['name']} {emp.get('surnames','')}"
            if len(punches) % 2 != 0:
                missing.append({"name": name, "code": emp["code"], "punches": len(punches), "last_punch": punches[-1].get("time","?") if punches else "none"})
            if len(punches) >= 2:
                try:
                    wd = await self.get_workday(emp.get("workday", ""))
                    s1 = wd.get("firstSession", {}).get("start", "")
                    s2 = wd.get("secondSession", {}).get("end", "")
                    if s1 and punches[0].get("time"):
                        diff = (int(punches[0]["time"][:2]) * 60 + int(punches[0]["time"][2:4])) - (int(s1[:2]) * 60 + int(s1[2:4]))
                        if diff > 15:
                            late.append({"name": name, "expected": s1, "actual": punches[0]["time"], "delay_min": diff})
                    if s2 and punches[-1].get("time"):
                        diff = (int(s2[:2]) * 60 + int(s2[2:4])) - (int(punches[-1]["time"][:2]) * 60 + int(punches[-1]["time"][2:4]))
                        if diff > 15:
                            early.append({"name": name, "expected": s2, "actual": punches[-1]["time"], "left_early_min": diff})
                except:
                    pass
        devices_status = await self.get_device_status()
        offline = [d for d in devices_status if not d.get("isConnected", True)]
        return {"date": date, "total_employees": len(employees), "missing_exit_punch": missing, "late_arrivals": late, "early_departures": early, "offline_devices": offline}
