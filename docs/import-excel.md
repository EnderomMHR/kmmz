# Import rozkładów Excel do KMMZ

## Co jest gotowe
- `tools/import-excel.py`: importer bez zewnętrznych bibliotek (Python 3), obsługuje XLSX.
- `data/import-config/5.json`: nazwy kierunków i nazwy plików zgodne z `linie/5.html`.
- `data/trips/005.json`: 36 kursów linii 5, z ID kursów i pełnymi czasami przystankowymi.
- `data/rozklady/linie/5.json`: format zgodny z obecnym `tools/generate-rozklady.py`.
- `tools/check-line5.py`: kontrola regresji danych linii 5.

## Jak dodać lub zaktualizować Excela
1. Zapisz źródłowy plik XLSX np. w `data/excel/5.xlsx` (lub użyj dowolnej ścieżki lokalnej).
2. Upewnij się, że aktualny **Arkusz1** zawiera `ID KURSU`, ID przystanków i godziny. **Arkusz2 jest ignorowany**.
3. Aby tylko sprawdzić poprawność: `python tools/import-excel.py --check data/excel/5.xlsx`.
4. Aby wygenerować JSON: `python tools/import-excel.py data/excel/5.xlsx`.
5. Aby wygenerować istniejące strony HTML i odjazdy: `python tools/generate-rozklady.py`.

Import opiera się na ID kursów, a nie stałej kolumnie. Minuty pomocnicze poza kolumnami z ID kursów są ignorowane. Nazwy i perony przystanków pochodzą z `data/stops/*.geojson`. Brakujący ID jest błędem. Zapisane wyniki formuł w XLSX są wymagane; importer nie oblicza samodzielnie formuł Excela.

## Dni kursowania
- `R` → `workday`;
- `S` → `saturday`;
- `N` → `sunday`;
- `SN` → `saturday` i `sunday`;
- `SW` → `holiday`.

`SW` wymaga dalszego ustalenia zasad kalendarzowych na stronie. Importer przenosi oznaczenia dni, lecz sam nie rozstrzyga, które daty podlegają poszczególnym regułom.

## Kierunki informacyjne linii okrężnych

Faktyczny kierunek jazdy (kolumna w Excelu, `direction` w `trips`) pozostaje bez zmian.
Jednak na każdym przystanku można wyświetlać **inny kierunek dla pasażera**:
w pliku `data/import-config/<numer>.json`, osobno dla każdego fizycznego kierunku
jazdy, dodaj opcjonalne `direction_segments`.

Przykład linii 7 (faktycznie **jeden** kierunek jazdy):

```json
"direction_segments": [
  {"from_stop_id": "0684", "name": "Chrzanów Fablok"},
  {"from_stop_id": "0682", "name": "Chrzanów Dworzec Autobusowy"}
]
```

- `from_stop_id` to **pierwszy przystanek**, na którym obowiązuje nowy kierunek informacyjny.
- Pierwszy segment musi zaczynać się na pierwszym przystanku trasy.
- Granice wyznacza się indywidualnie dla każdej linii, np. na trzecim, piątym
  lub dziesiątym przystanku — **nie ma stałej pozycji zmiany kierunku**.
- Linie okrężne dwukierunkowe mogą mieć osobną listę segmentów w każdej
  z dwóch konfiguracji kierunków.
- Kierunki są używane w HTML rozkładu, na stronach przystanków i w panelu mapy.
- Kurs kończący jazdę na danym przystanku nadal nie jest odjazdem.
- Jeśli pole `direction_segments` pominięto, obowiązuje dotychczasowe `name`
  i dotychczasowe zachowanie pozostałych linii nie ulega zmianie.

## Ograniczenia pierwszej wersji
- Importer wymaga uprzednio nadanych ID kursów i ID przystanków oraz konfiguracji każdego nowego numeru linii.
- Kursy przechodzące przez północ lub powtarzające ten sam ID przystanku w jednym kierunku wymagają osobnej obsługi.
- Dodatkowe warianty tras i skrócenia kursów wymagają dalszych testów, zwłaszcza gdy kilka wariantów dzieli jeden kierunek.
- Excel opisuje kolejność przystanków i czasy, a nie geometrię dróg; nie generujemy na jego podstawie fikcyjnych tras ulicznych.
- Wersja próbna nie zastępuje generatora HTML i nie publikuje automatycznie XLSX; obecny mechanizm GitHub Actions nadal reaguje na JSON-y.

## Bezpieczeństwo
Zmiany zostały przygotowane na gałęzi roboczej do zatwierdzenia przed włączeniem do `main`. Nie importuj do `main` niezweryfikowanych danych.
