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

Kiedy pierwszy i ostatni przystanek pełnego przebiegu mają ten sam `stop_id`,
importer automatycznie dodaje **oddzielną stronę końcowego przyjazdu**
`<ID>-<slug>-koniec.html` i oznacza jej rekord `arrival_only: true`.
Na takiej stronie nie ma odjazdów; w danych mapy i na fizycznej stronie
przystanku pozostają wyłącznie rzeczywiste odjazdy z danego ID.
Strona przebiegu linii powinna odsyłać z ostatniej pozycji do tej
oddzielnej strony (nie do rozkładu początkowego). Nie dodawaj odrębnego
przystanku do GeoJSON.

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

## Powtarzany przystanek z kontynuacją części kursów (np. linia 9)

Importer generuje osobny rozkład dla **każdego wystąpienia przystanku**
w ramach jednego kierunku, niezależnie od wspólnego fizycznego `stop_id`.
Przykład: `0001-okrezna-2.html` (odjazdy na początku) i
`0001-okrezna-2-ponownie.html` (odjazdy przy drugim przejeździe).
Ostatnia wizyta każdego konkretnego kursu jest przyjazdem i nie
jest uwzględniana w żadnej liście odjazdów. Wariant, który jedzie dalej
z drugiego wystąpienia, zachowuje swoje rzeczywiste odjazdy.

W `data/odjazdy/<ID>.json` / na mapie i fizycznej stronie przystanku
wszystkie odjazdy z obu wystąpień łączone są pod jednym `stop_id`,
zachowując odnośnik do odpowiedniej, oddzielnej strony rozkładu linii.

Konfiguracja `variant_symbol_starts` przypisuje kod wariantu do ID
przystanku, od którego dopiero należy wyświetlać jego literę, np.
`{"1": "0711"}` z `variant_symbols: {"1": "W"}`.
Wcześniejsze odjazdy tego wariantu nie dostają litery, natomiast od
wskazanej pozycji mają symbol i wyświetlaną nazwę kierunku z
`variant_destinations: {"W": "Wolbrom Pod Lasem"}`.
To nie zmienia ID kursu, tylko informację pasażerską.


### Zakończenie oznaczania wariantu po zmianie wyświetlanego kierunku

Litera jest potrzebna tylko na odcinku, na którym wyróżnia jedną
z kilku możliwych destynacji. W konfiguracji kierunku można ustawić
`variant_symbol_ends`, np. `{"1": {"stop_id": "0001", "occurrence": 2}}`.
Numer `occurrence` rozróżnia wizyty na tym samym fizycznym przystanku.
Od wskazanego wystąpienia litera zostaje pominięta w rozkładach, a gdy
dany fragment trasy obsługuje wyłącznie ten wariant, kierunek na
stronie i mapie zostaje ustawiony bezpośrednio na destynację wariantu.
Taka strona nie wyświetla legendy nieużywanej litery.

Przykład z linii 9, kierunek 2: `W` pojawia się od przystanku `0711`
do `0021` włącznie. Od **drugiego** `0001` przez `0029` do `0016`
kursy jadą tylko do Wolbrom Pod Lasem, więc godziny są bez `W`,
a nazwa kierunku to `Wolbrom Pod Lasem`. Przystanek `0015` jest
końcowy i nie publikuje godzin przyjazdów jako odjazdów.


## Linia 10 – okrężna dwukierunkowa bez wariantów

Dane wejściowe: tylko **Arkusz1** ze zaktualizowanego
`P.A.M. - Linia 10 (1).xlsx` (13 kursów, 420 czasów przejazdu).
Wszystkie ID mają wariant `0`, również kurs
`010-2-0-R-03` rozpoczynający się na przystanku `0106`.
Nie tworzymy dodatkowej litery wariantu wyłącznie ze względu
na późniejszy początek kursu.

Kierunki informacyjne zgodne z `data/import-config/10.json`:
- Kierunek 1: od początkowego `0147` do `0734` włącznie
  **Bukowno Bór Biskupi OSP**; od `0735` do końca
  **Bukowno Dworzec PKP**.
- Kierunek 2: od początkowego `0147` do `0256` włącznie
  **Bukowno Przymiarki**; od `0106` do końca
  **Bukowno Dworzec PKP**.

Końcowe wystąpienie `0147` w każdym kierunku ma osobną stronę
`-koniec.html` bez odjazdów. Fizyczny przystanek `0147`
pozostaje pojedynczy w GeoJSON oraz na mapie.
Godziny przyjazdów końcowych są zachowane w `data/trips/010.json`,
ale nie są wyświetlane jako odjazdy. Arkusz2 pomijamy.


## Linia 11 – niezależne oznaczenia P i Z, zawsze w kolejności alfabetycznej

Źródło: `P.A.M. - Linia 11.xlsx` (wyłącznie Arkusz1), po poprawieniu
`011-1-2-R-03` → `011-1-1-R-03`. Plik zawiera 84 kursy,
3254 godziny przejazdów, 3170 odjazdów (po odjęciu końcowych przyjazdów).
Tabelę wklejoną wcześniej do czatu porównano z Excelem komórka po komórce;
jedyną różnicą był poprawiony identyfikator.

- Kierunek 1: **Tarnawa Podlas**; dla kursów przedłużonych do Poręby
  oznaczenie **P = do: Poręba Laskowska**. Na ostatnim, wyłącznie
  porębskim odcinku od `0755` nagłówek strony i kierunek na mapie to
  **Poręba Laskowska** bez dodatkowej litery.
- Kierunek 2: **Olkusz Dworzec PKS**.
- **Z = przez: Zagórowa**. Literę Z wyświetlamy tylko *przed*
  pierwszym `0770 Milonki II (2)`. Od `0770` i na dalszej
  części trasy nie ma już potrzeby zapowiadać rozpoczętego przejazdu
  wariantowego (dotyczy obu kierunków).
- Dla kursów z obiema cechami litery mają **zawsze** kolejność
  alfabetyczną `PZ`, nie `ZP`. Po wjeździe w Zagórową zostaje `P`,
  a od `0755` zostaje jedynie destynacja „Poręba Laskowska”.
- Legenda jest posortowana alfabetycznie i wyświetla tylko litery,
  które występują w rzeczywistych godzinach na danej stronie.
- Odjazdy końcowe nie są fabrykowane: `0747 Poręba Laskowska`
  (kierunek 1) oraz `0200 Olkusz Dworzec PKS` (kierunek 2)
  mają stronę końcową bez godzin odjazdów.

Nowe pole `variant_letter_ends` jest mapą *pojedynczej litery*
na `{"stop_id":"0770","occurrence":1}`. Dzięki temu złożony
wariant `PZ` może stracić samą literę `Z` bez wyłączania `P`.
Zachowano dotychczasowe pole `variant_symbol_ends` dla linii 9.
Pole `legend_only_used_symbols` oznacza wyświetlanie tylko
aktywnych liter na konkretnej stronie przystankowej.


## Linia 12 — klasyczna dwukierunkowa, bez wariantów

Źródło: `P.A.M. - Linia 12.xlsx`, wyłącznie arkusz `Arkusz1`.
45 kursów (kierunek 1: 23, kierunek 2: 22), 2723 czasy
przejazdu, 2678 rzeczywistych odjazdów.
Wszystkie 2678 formuł czasu mają zapisane wartości obliczeń.

- Kierunek 1: `Jawiszowice Kółko (2)` → `Mętków Mały (0)`,
  `metkow`, 61 przystanków, przejazd 95 minut.
- Kierunek 2: `Mętków Mały (0)` → `Jawiszowice Kółko (1)`,
  `jawiszowice`, 60 przystanków, przejazd 94 minuty.
- Wariant `0` we wszystkich kursach; nie używamy liter,
  segmentów kierunku informacyjnego ani legend.
- W dni robocze po 13 kursów w każdym kierunku, w soboty
  i niedziele odpowiednio 7 i 6 (`SN`: wspólny rozkład dla
  obu dni), w święta po 3 kursy.
- Każdy kurs jedzie całą trasą; nie ma skróceń ani wypadania
  pojedynczych przystanków.
- Końcowy `0311 Mętków Mały` w kierunku 1 oraz końcowy
  `2557 Jawiszowice Kółko` w kierunku 2 mają dedykowane
  strony bez odjazdów. Przyjazdy końcowe zapisujemy w kursach,
  ale nie przenosimy ich na mapę jako odjazdy.
- Wszystkie przystanki i linki na `linie/12.html` są poprawne;
  nie trzeba zmieniać dotychczasowej strony trasy.

Testy: `tools/test-line12-import.py` regeneruje dane z
wierszy odpowiadających Arkusz1, a `tools/check-line12.py`
porównuje wszystkie kursy z niezależnym odciskiem SHA-256
arkusza i sprawdza strony, dni SN/SW, kierunki i mapowe
przystanki początkowe/końcowe.
