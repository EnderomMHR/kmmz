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

## Kiedy nadać nowy numer wariantu w ID kursu?

**Nie trzeba tworzyć wariantu tylko dlatego, że kurs zaczyna wcześniej lub
później na tej samej trasie.** Dla kursów o wspólnym końcu i identycznym
przebiegu dalszej trasy można użyć tego samego kodu wariantu (np. `0`).

Przykład: oba kursy mogą mieć wariant `0`:

- `008-1-0-R-01`: A → B → C → D (pełna trasa)
- `008-1-0-R-02`: B → C → D (ten sam wariant, późniejszy początek)

Konwerter identyfikuje wzorcowy przebieg wariantu na podstawie najdłuższego
kursu. Krótszy kurs musi być **ciągłym końcowym fragmentem** tego przebiegu
(tzw. suffix), z tym samym przystankiem końcowym. Dzięki temu mogą występować
różne przystanki początkowe; w `data/trips/NNN.json` poszczególne kursy
zachowują rzeczywiste początki, a tabela rozkładowa zawiera tylko godziny
tych kursów, które faktycznie obsługują dany przystanek.

**Osobny kod wariantu nadal jest potrzebny**, kiedy:
- kurs kończy jazdę na innym przystanku (wcześniej lub dalej);
- kurs jedzie innymi ulicami/przystankami albo pomija przystanek pośrodku
  wzorcowego przebiegu;
- dodatkowy początek to w istocie inna odnoga (nie przedłużenie tej samej trasy).

Przykładowe błędy, jeśli oba kursy mają kod `0`: `A → B → C → D`
oraz `A → B → C` (inna końcówka) lub `A → X → C → D` (inna trasa).
Importer wstrzyma się z czytelnym komunikatem, zamiast błędnie połączyć
dwa różne przebiegi.

**Litery w rozkładach** (`Z`, `O` itd.) pozostają przypisane przez
`variant_symbols` w `data/import-config/NNN.json`. Zmiana miejsca
rozpoczęcia kursu **nie zmienia litery**, jeżeli kod wariantu pozostaje ten sam.
Kursy kończące się na przystanku końcowym nadal nie pokazują tam fikcyjnego
odjazdu.

Excel nadal wymaga części wariantu w ID kursu, np. `008-1-0-R-02`,
ale możesz używać **tego samego numeru** dla różnych początków. Konwerter
nie nadaje automatycznie nowych numerów ani nie zgaduje, jaka litera ma
oznaczać zmienioną trasę.

## Powtarzające się przystanki na trasie (linie okrężne)

Ten sam fizyczny przystanek (np. `0200`) **może wystąpić kilka razy** w
`Arkusz1`, również jako początek i koniec kursu. Nie zmieniaj poprawnych
ID przystanków w Excelu tylko dlatego, że linia wraca w to samo miejsce.

- W `data/trips/NNN.json` wszystkie wystąpienia zostają zachowane
  w kolejności `stop_times` / `stop_sequence`.
- W rozkładach na stronie i w danych mapy ostatnia pozycja **każdego
  kursu** jest przyjazdem końcowym, a nie odjazdem. Pozostałe wizyty
  (także na tym samym ID) nadal są uwzględniane jako odjazdy.
- Dla fizycznego ID przystanku powstaje tylko jeden rekord rozkładu,
  nawet jeśli przystanek występuje kilka razy na trasie; wszystkie
  rzeczywiste odjazdy są w tym rekordzie.
- `route_stops` zachowuje kolejność pełnego przebiegu z powtórzeniami,
  aby nie usuwać odcinków pętli.
- Łączenie bloków tego samego kierunku zachowuje kolejne wystąpienia ID.
  W przypadku rozbieżnych wariantów wspólna lista przystanków nadal jest
  widokiem zbiorczym; przebieg konkretnego kursu jest w `trips`.

Arkusz2 jest pomijany. Specjalne wyjątki świąteczne z tego arkusza
nie są importowane.

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
- Kursy przechodzące przez północ wymagają osobnej obsługi.
- Odmienne przebiegi i skrócenia końca kursu wymagają osobnych kodów wariantów i konfiguracji oznaczeń pasażerskich; zmienne początki tej samej trasy są obsługiwane.
- Excel opisuje kolejność przystanków i czasy, a nie geometrię dróg; nie generujemy na jego podstawie fikcyjnych tras ulicznych.
- Wersja próbna nie zastępuje generatora HTML i nie publikuje automatycznie XLSX; obecny mechanizm GitHub Actions nadal reaguje na JSON-y.

## Bezpieczeństwo
Zmiany zostały przygotowane na gałęzi roboczej do zatwierdzenia przed włączeniem do `main`. Nie importuj do `main` niezweryfikowanych danych.
