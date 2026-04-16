"""
Gemini AI Engine - Natural language to GTC API calls.
Uses function calling to map WhatsApp messages to GoTimeCloud operations.
"""
import json
import logging
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from app.config import settings
from app.gtc_client import GTCClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente de GoTimeCloud, el sistema de gestion de presencia y tiempo de trabajo de ZKTeco.

Respondes en espanol de forma concisa y directa, sin markdown.
Gestionas empleados, fichajes, horarios, vacaciones, dispositivos y mas.

REGLAS:
- Siempre confirma las acciones realizadas
- Para buscar empleados, usa parte del nombre
- Los codigos de empleado son 9 digitos numericos
- Las fechas van en formato YYYYMMDD (ej: 20260501 = 1 de mayo 2026)
- Los eventos: 0000=Trabajo, 0004=Vacaciones, 0003=Baja, 0005=Permiso, 0001=Ausencia justificada, 0002=Baja medica
- Si no encuentras un empleado, pregunta por el nombre completo
- Si algo falla, explica que paso de forma simple
- Para resumenes usa el formato: nombre del campo seguido de su valor, una por linea

CAPACIDADES:
- Listar y buscar empleados
- Crear, actualizar y eliminar empleados
- Ver fichajes de hoy o de una fecha concreta
- Registrar fichajes manuales
- Ver resumen del dia (llegadas tarde, fichajes faltantes, dispositivos caidos)
- Ver fichajes faltantes (sin cierre)
- Gestionar vacaciones y ausencias
- Consultar horarios, perfiles, calendarios
- Ver estado de dispositivos
- Consultar centros y departamentos
- Ver acumulados de un empleado
- Ver informacion de la suscripcion
"""


def _get_tools_schema() -> list:
    """Define the function calling tools for Gemini."""
    return [
        {
            "name": "list_employees",
            "description": "Lista todos los empleados de la empresa. Devuelve nombre, codigo, departamento y centro.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "find_employee",
            "description": "Busca un empleado por nombre o NIF. Devuelve todos sus datos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Parte del nombre a buscar"},
                    "nif": {"type": "string", "description": "NIF del empleado"}
                }
            }
        },
        {
            "name": "create_employee",
            "description": "Crea un nuevo empleado. El codigo se genera automaticamente.",
            "parameters": {
                "type": "object",
                "required": ["name", "surnames"],
                "properties": {
                    "name": {"type": "string", "description": "Nombre"},
                    "surnames": {"type": "string", "description": "Apellidos"},
                    "department": {"type": "string", "description": "Codigo departamento (5 digitos, default 00000)"},
                    "center": {"type": "string", "description": "Codigo centro (5 digitos, default 00000)"},
                    "workday": {"type": "string", "description": "Codigo horario (4 digitos, default 0000)"},
                    "nif": {"type": "string", "description": "NIF/DNI"},
                    "mail": {"type": "string", "description": "Email"},
                    "telephone": {"type": "string", "description": "Telefono"}
                }
            }
        },
        {
            "name": "update_employee",
            "description": "Actualiza datos de un empleado. Solo se envian los campos a cambiar.",
            "parameters": {
                "type": "object",
                "required": ["code", "field", "value"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado (9 digitos)"},
                    "field": {"type": "string", "description": "Campo a actualizar: name, surnames, department, center, workday, nif, mail, telephone"},
                    "value": {"type": "string", "description": "Nuevo valor"}
                }
            }
        },
        {
            "name": "delete_employee",
            "description": "Elimina un empleado del sistema.",
            "parameters": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado (9 digitos)"}
                }
            }
        },
        {
            "name": "get_punches_today",
            "description": "Obtiene los fichajes de hoy para un empleado.",
            "parameters": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado (9 digitos)"}
                }
            }
        },
        {
            "name": "get_punches_date",
            "description": "Obtiene fichajes de un empleado en una fecha concreta.",
            "parameters": {
                "type": "object",
                "required": ["code", "date"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado"},
                    "date": {"type": "string", "description": "Fecha en formato YYYYMMDD"}
                }
            }
        },
        {
            "name": "register_punch",
            "description": "Registra un fichaje manual para un empleado.",
            "parameters": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado"},
                    "date": {"type": "string", "description": "Fecha YYYYMMDD (opcional, default hoy)"},
                    "time": {"type": "string", "description": "Hora HHMMSS (opcional, default ahora)"}
                }
            }
        },
        {
            "name": "daily_summary",
            "description": "Resumen del dia: llegadas tarde, fichajes faltantes, dispositivos caidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Fecha YYYYMMDD (opcional, default hoy)"}
                }
            }
        },
        {
            "name": "check_missing_punches",
            "description": "Busca empleados con fichajes sin cierre (numero impar de fichajes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Fecha YYYYMMDD (opcional, default hoy)"}
                }
            }
        },
        {
            "name": "request_vacation",
            "description": "Solicita vacaciones para un empleado en un rango de fechas.",
            "parameters": {
                "type": "object",
                "required": ["code", "date_from", "date_to"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado"},
                    "date_from": {"type": "string", "description": "Fecha inicio YYYYMMDD"},
                    "date_to": {"type": "string", "description": "Fecha fin YYYYMMDD"}
                }
            }
        },
        {
            "name": "set_absence",
            "description": "Registra una ausencia o baja para un empleado.",
            "parameters": {
                "type": "object",
                "required": ["code", "date", "event_code"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado"},
                    "date": {"type": "string", "description": "Fecha YYYYMMDD"},
                    "event_code": {"type": "string", "description": "Codigo evento: 0001=Ausencia justificada, 0002=Baja medica, 0003=Baja, 0005=Permiso"}
                }
            }
        },
        {
            "name": "list_workdays",
            "description": "Lista los horarios/jornadas configurados.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "list_devices",
            "description": "Lista dispositivos y su estado de conexion.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "list_centers",
            "description": "Lista los centros de trabajo.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "list_departments",
            "description": "Lista los departamentos.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_accruals",
            "description": "Obtiene los acumulados (horas trabajadas, extras, etc) de un empleado.",
            "parameters": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string", "description": "Codigo del empleado"},
                    "year": {"type": "string", "description": "Ano (default actual)"}
                }
            }
        },
        {
            "name": "get_subscription",
            "description": "Muestra informacion de la suscripcion de GoTimeCloud.",
            "parameters": {"type": "object", "properties": {}}
        },
    ]


async def execute_tool(gtc: GTCClient, tool_name: str, args: dict) -> str:
    """Execute a GTC API call based on tool name and arguments."""
    try:
        if tool_name == "list_employees":
            emps = await gtc.list_employees()
            if not emps:
                return "No hay empleados."
            lines = [f"{e['code']} | {e['name']} {e.get('surnames', '')} | Dept: {e.get('department', '')} | Activo: {'Si' if e.get('active') else 'No'}" for e in emps[:30]]
            return f"{len(emps)} empleados:\n" + "\n".join(lines)

        elif tool_name == "find_employee":
            emp = await gtc.find_employee(name=args.get("name"), nif=args.get("nif"))
            if not emp:
                return "Empleado no encontrado. Prueba con otro nombre."
            return json.dumps(emp, ensure_ascii=False, indent=2)

        elif tool_name == "create_employee":
            existing = await gtc.list_employees()
            next_code = str(max(int(e["code"]) for e in existing) + 1).zfill(9) if existing else "000000001"
            r = await gtc.create_employee(next_code, args["name"], args["surnames"],
                                          **{k: v for k, v in args.items() if k not in ("name", "surnames")})
            if r["status"]["code"] == 200:
                return f"Empleado creado: {args['name']} {args['surnames']} con codigo {next_code}"
            return f"Error al crear: {r['status']['message']}"

        elif tool_name == "update_employee":
            r = await gtc.update_employee(args["code"], **{args["field"]: args["value"]})
            if r["status"]["code"] == 200:
                return f"Actualizado {args['field']} = {args['value']} para empleado {args['code']}"
            return f"Error: {r['status']['message']}"

        elif tool_name == "delete_employee":
            r = await gtc.delete_employee(args["code"])
            if r["status"]["code"] == 200:
                return f"Empleado {args['code']} eliminado."
            return f"Error: {r['status']['message']}"

        elif tool_name == "get_punches_today":
            punches = await gtc.get_today_punches(args["code"])
            if not punches:
                return "Sin fichajes hoy."
            return "Fichajes de hoy:\n" + "\n".join(f"  {p.get('time', '?')} ({p.get('event', '0000')})" for p in punches)

        elif tool_name == "get_punches_date":
            punches = await gtc.get_employee_punches(args["code"], args["date"], args["date"])
            if not punches:
                return f"Sin fichajes el {args['date']}."
            return f"Fichajes del {args['date']}:\n" + "\n".join(f"  {p.get('time', '?')} ({p.get('event', '0000')})" for p in punches)

        elif tool_name == "register_punch":
            date = args.get("date") or datetime.now().strftime("%Y%m%d")
            time = args.get("time") or (datetime.utcnow() + timedelta(hours=gtc.utc)).strftime("%H%M%S")
            r = await gtc.register_punch(args["code"], date, time)
            if r["status"]["code"] == 200:
                return f"Fichaje registrado: {date} a las {time} para empleado {args['code']}"
            return f"Error: {r['status']['message']}"

        elif tool_name == "daily_summary":
            s = await gtc.daily_summary(args.get("date"))
            lines = [f"Resumen del {s['date']}",
                     f"Empleados: {s['total_employees']} (con fichajes: {s.get('employees_with_punches', '?')})"]
            if s["missing_exit_punch"]:
                lines.append(f"Fichajes sin salida ({len(s['missing_exit_punch'])}):")
                for m in s["missing_exit_punch"][:5]:
                    lines.append(f"  {m['name']}: {m['punches']} fichajes, ultimo {m['last_punch']}")
            if s.get("late_arrivals"):
                lines.append(f"Llegadas tarde ({len(s['late_arrivals'])}):")
                for l in s["late_arrivals"]:
                    lines.append(f"  {l['name']}: +{l['delay_min']}min")
            if s.get("early_departures"):
                lines.append(f"Salidas anticipadas ({len(s['early_departures'])}):")
                for e in s["early_departures"]:
                    lines.append(f"  {e['name']}: -{e['left_early_min']}min")
            if s["offline_devices"]:
                lines.append(f"Dispositivos offline: {len(s['offline_devices'])}")
            if not s["missing_exit_punch"] and not s.get("late_arrivals") and not s.get("early_departures"):
                lines.append("Sin anomalias.")
            return "\n".join(lines)

        elif tool_name == "check_missing_punches":
            missing = await gtc.check_missing_punches(args.get("date"))
            if not missing:
                return "Todos los fichajes estan cerrados."
            return f"Empleados con fichajes sin cierre ({len(missing)}):\n" + "\n".join(
                f"  {m['name']}: {m['punches']} fichajes, ultimo {m['last_punch']}" for m in missing[:10])

        elif tool_name == "request_vacation":
            r = await gtc.create_petition(args["code"], "0004", args["date_from"], args["date_to"])
            if r["status"]["code"] == 200:
                return f"Vacaciones solicitadas para {args['code']} del {args['date_from']} al {args['date_to']}"
            return f"Error: {r['status']['message']}"

        elif tool_name == "set_absence":
            r = await gtc.set_employee_status(args["code"], args["date"], args["event_code"])
            if r["status"]["code"] == 200:
                return f"Ausencia registrada para empleado {args['code']} el {args['date']}"
            return f"Error: {r['status']['message']}"

        elif tool_name == "list_workdays":
            wds = await gtc.list_workdays()
            return "Horarios:\n" + "\n".join(f"  {w['code']} | {w['description']}" for w in wds)

        elif tool_name == "list_devices":
            devs = await gtc.list_devices()
            status = await gtc.get_device_status()
            status_map = {d["code"]: d.get("isConnected", "?") for d in status}
            return "Dispositivos:\n" + "\n".join(
                f"  {d['code']} | {d.get('description', '?')} | Online: {'Si' if status_map.get(d['code']) else 'No'}"
                for d in devs)

        elif tool_name == "list_centers":
            centers = await gtc.list_centers()
            return "Centros:\n" + "\n".join(f"  {c['code']} | {c['description']}" for c in centers)

        elif tool_name == "list_departments":
            depts = await gtc.list_departments()
            return "Departamentos:\n" + "\n".join(f"  {d['code']} | {d['description']}" for d in depts)

        elif tool_name == "get_accruals":
            accruals = await gtc.get_accruals(args["code"], args.get("year"))
            if not accruals:
                return "Sin acumulados."
            return "Acumulados:\n" + "\n".join(
                f"  {a.get('description', '?')}: {a.get('totalTime', 0)} min ({a.get('totalOcurrences', 0)} veces)"
                for a in accruals)

        elif tool_name == "get_subscription":
            sub = await gtc.get_subscription()
            return json.dumps(sub, ensure_ascii=False, indent=2)

        else:
            return f"Herramienta desconocida: {tool_name}"

    except Exception as e:
        logger.error(f"Tool error {tool_name}: {e}")
        return f"Error al ejecutar {tool_name}: {str(e)}"


async def process_message(gtc: GTCClient, message: str, history: list[dict]) -> str:
    """Process a WhatsApp message through Gemini with function calling."""
    client = genai.Client(api_key=settings.gemini_api_key)

    # Build conversation
    contents = []
    for msg in history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    # Add current message
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    tools = types.Tool(function_declarations=_get_tools_schema())
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[tools],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    # Call Gemini
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=config,
    )

    # Handle function calls
    if response.candidates and response.candidates[0].content.parts:
        tool_results = []
        for part in response.candidates[0].content.parts:
            if part.function_call:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                logger.info(f"Gemini calls: {fc.name}({args})")
                result = await execute_tool(gtc, fc.name, args)
                tool_results.append({
                    "name": fc.name,
                    "args": args,
                    "result": result,
                })

        if tool_results:
            # Send tool results back to Gemini for final response
            func_response_parts = []
            for tr in tool_results:
                func_response_parts.append(types.Part.from_function_response(
                    name=tr["name"],
                    response={"result": tr["result"]},
                ))

            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=func_response_parts))

            final_response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=config,
            )
            return final_response.text or "No pude procesar la solicitud."

    # Direct text response (no function call)
    return response.text or "No entendi tu mensaje. Puedo ayudarte con empleados, fichajes, horarios, vacaciones y mas."
