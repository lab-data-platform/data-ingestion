"""Servidor que faz o papel da API SGS do BCB no ambiente local, a partir das fixtures gravadas.

Responde a /dados/serie/bcdata.sgs.<serie>/dados?dataInicial=dd/mm/aaaa&dataFinal=...:
- 29/10/2026 → janela entre dois dias úteis (2 observações);
- 30/10/2026 → sexta para sábado (1 observação);
- qualquer outra data → 404, como a API real em fins de semana e feriados.
"""

import http.server
import pathlib
import urllib.parse

FIXTURES = pathlib.Path("/fixtures")
RESPONSES = {
    "29/10/2026": (200, "window_two_business_days.json"),
    "30/10/2026": (200, "window_friday_saturday.json"),
}
NOT_FOUND = (404, "window_weekend_404.json")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        status, file_name = RESPONSES.get(query.get("dataInicial", [""])[0], NOT_FOUND)
        body = (FIXTURES / file_name).read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
