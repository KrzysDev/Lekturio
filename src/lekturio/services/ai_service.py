import logging

from ollama import chat, ChatResponse


logger = logging.getLogger(__name__)


class AiService:

    def __init__(
        self,
        model: str = "SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q8_0",
        temperature: float = 0.1,
        num_ctx: int = 16384,
        num_predict: int = 1000,
        seed: int | None = 42,
    ):
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self.seed = seed

    def ask(
        self,
        prompt: str,
        response_format: dict | None = None
    ) -> str:

        options = {
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }
        if self.seed is not None:
            options["seed"] = self.seed

        logger.info(
            "Ollama request: model=%s prompt_chars=%d temperature=%s "
            "num_ctx=%s num_predict=%s seed=%s",
            self.model, len(prompt), self.temperature,
            self.num_ctx, self.num_predict, self.seed,
        )
        response: ChatResponse = chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            format=response_format,
            options=options,
        )

        prompt_eval_count = getattr(response, "prompt_eval_count", None)
        eval_count = getattr(response, "eval_count", None)
        done_reason = getattr(response, "done_reason", None)
        logger.info(
            "Ollama response: prompt_eval_count=%s eval_count=%s done_reason=%s",
            prompt_eval_count, eval_count, done_reason,
        )
        if done_reason == "length":
            logger.warning(
                "Ollama stopped at a generation limit (done_reason=length); "
                "the answer may be incomplete (num_predict=%s).",
                self.num_predict,
            )
        if (
            prompt_eval_count is not None
            and self.num_ctx > 0
            and prompt_eval_count >= self.num_ctx * 0.9
        ):
            logger.warning(
                "Ollama prompt_eval_count=%s is approaching num_ctx=%s; "
                "this is a context-pressure diagnostic, not proof of truncation.",
                prompt_eval_count, self.num_ctx,
            )

        content = getattr(getattr(response, "message", None), "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Ollama returned missing or blank message content for model {self.model!r} "
                f"(done_reason={done_reason!r})."
            )

        return content


if __name__ == "__main__":

    ai_service = AiService()

    print(
        ai_service.ask(
            """na podstawie ponizszego fragmentu odpowiedz w jaki sposob umiera Hajmon. Podaj odpowiednie cytaty: 
            
                [
                {
                    "id": "sofokles_antygona_0019",
                    "title": "Antygona",
                    "author": "Sofokles",
                    "chunk_index": 19,
                    "similarity": 0.582926151447458,
                    "fragment": "bogactwa do woli w twym domu,\nŚwieć jako władca na zewnątrz: gdy cieszyć\nTym się nie można, to reszty tych skarbów\nJa bym nie nabył za dymu cień marny.\nPrzodownik Chóru\nJakąż ty znowu wieść niesiesz złą księciu?\nPosłaniec\nSkończyli... Śmierci ich winni, co żyją.\nPrzodownik Chóru\nKtóż to mordercą, któż poległ? O, rzeknij!\nPosłaniec\nHaimon nie żyje, we własnej krwi broczy.\nPrzodownik Chóru\nZ ojca czy z własnej zginąłże on ręki?\nPosłaniec\nW gniewie na ojca mordy sam się zabił.\nPrzodownik Chóru\nWróżbito, jakżeś czyn trafnie określił!\nPosłaniec\nW tym rzeczy stanie dalszej trza narady.\nPrzodownik Chóru\nLecz oto widzę biedną Eurydykę,\nŻonę Kreona; albo się przypadkiem\nPojawia, albo słyszała o synu.\nZ pałacu wychodzi E u r y d y k a .\nEurydyka\nStarcy, rozmowy waszej posłyszałam\nWłaśnie, gdym z domu wybiec zamierzała,\nBy do Pallady z modłami się zwrócić.\nI właśnie odrzwi odmykam zasuwki,\nBy je roztworzyć, gdy nagle nieszczęsna\nWieść uszy rani; więc padłam, zemdlona\nZ trwogi, w objęcia mych wiernych służebnic.\nPowtórzcie tedy, co ta wieść przynosi;\nW złym doświadczona, wysłucham słów waszych.\nPosłaniec\nJa, miłościwa pani, byłem przy tym,\nPowiem więc wszystko, jak się wydarzyło;\n39\nCóż bo ukrywać, by potem na kłamcę\nWyjść? Przecie prawda zawsze fałsz przemoże.\nJa tedy wiodłem twojego małżonka\nNa ten pagórek, gdzie biedne leżało,\nPrzez psy podarte, ciało Polinika.\nWnet do Hekaty zanieśliśmy modły\nI do Plutona, by gniew ich złagodzić;\nObmywszy potem ciało w świętej wodzie,\nPalimy szczątki na stosie z gałęzi\nI grób z ojczystej sypiemy im ziemi.\nTo uczyniwszy, zaraz do kamiennej\nŚlubno-grobowej łożnicy dziewczyny\nŚpieszymy. Z dala ktoś jęki usłyszał\nOd strony lochu, co za grób miał służyć,\nChoć nie święciły go żadne obrzędy.\nWraz więc donosi panu, co zasłyszał.\nTego dochodzą zaś, kiedy się zbliżył,\nŁkania żałosne, a pierś mu wybucha\nGłosem rozpaczy: „O, ja nieszczęśliwy!\nCzym odgadł prawdę? Czyż nie kroczę teraz\nDrogą największej w żywocie mym klęski?\nSyna wołanie mnie mrozi. O słudzy,\nŚpieszcie wy naprzód, zbliżcie się do grobu\nI przez szczelinę głazem zawaloną\nWszedłszy do wnętrza, baczcie, czy Haimona\nGłosy ja słyszę, czy bogi mnie durzą”.\nPosłuszni woli zwątpiałego pana,\nIdziem na zwiad, a w grobowca głębi\nDojrzym wnet dziewkę, wiszącą za gardło,\nŚciśnięte węzłem muślinowej chusty,\nPodczas gdy młodzian uchwycił ją wpoły,\nBoleśnie jęcząc nad szczęścia utratą,\nNad czynem ojca, nieszczęsnymi śluby.\nKreon, zoczywszy to, ciężko zajęknął,\nRzuca się naprzód i wśród łkania woła:\n„O ty nieszczęsny! Cóżeś ty uczynił!\nCzy szał cię jaki opętał złowrogi?\nWychodź, o synu, błagalnie cię proszę!”\nLecz syn na niego dzikim łysnął wzrokiem\nI twarz przekrzywił, a słowa nie rzekłszy\nIma się miecza: wraz ojciec ucieczką\nUszedł zamachu; natenczas nieszczęsny\nW gniewie na siebie nad ostrzem się schyla\nI miecz w bok wraża; lecz jeszcze w konaniu\nDrętwym ramieniem do zmarłej się tuli,\nA z ust dyszących wytryska mu struga\nKrwawa na blade kochanki policzki.\nE u r y d y k a wybiega do pałacu.\nTrup dziś przy trupie, osiągnął on śluby,\n40\nW domu Hadesa złożony przy lubej.\nNieszczęściem"
                },
                {
                    "id": "sofokles_antygona_0013",
                    "title": "Antygona",
                    "author": "Sofokles",
                    "chunk_index": 13,
                    "similarity": 0.5540967188902279,
                    "fragment": "pustyni.\nKreon\nTen, jak się zdaje, z tamtą dziewką trzyma.\nHaimon\nJeśli ty dziewką: o ciebie się troskam.\nKreon\nZ ojcem się swarząc, o przewrotny synu?\nHaimon\nBo widzę, że ty z drogi zbaczasz prawej.\nKreon\nBłądzęż ja strzegąc godności mej władzy?\nHaimon\nNie strzeżesz – władzą pomiatając bogów.\nKreon\nO niski duchu, na służbie kobiety!\nHaimon\nLecz w służbie złego nie znajdziesz mnie nigdy.\nKreon\nCała twa mowa jej sprawy ma bronić.\nHaimon\nTwej sprawy, mojej i podziemnych bogów.\n26\nKreon\nNigdy już żywej ty jej nie poślubisz.\nHaimon\nZginie – to śmiercią sprowadzi zgon inny.\nKreon\nA więc już groźbą śmiesz we mnie ty godzić?\nHaimon\nNie godzę: zwalczyć puste chcę zamysły.\nKreon\nWnet pożałujesz twych nauk, młokosie!\nHaimon\nNie byłbyś ojcem, rzekłbym, żeś niemądry.\nKreon\nNiewiast służalcze, przestań się uprzykrzać!\nHaimon\nChcesz więc ty mówić, a drugich nie słuchać?\nKreon\nDoprawdy? Ale, na Olimp, wiedz o tym,\nŻe cię twe drwiny o zgubę przyprawią.\nWiedźcie tu dziewkę; niechajże wyrodna\nW oczach kochanka tu ginie, natychmiast!\nHaimon\nNie umrze ona przy mnie! Nie marz o tym!\nNie ujrzę tego, raczej ty nie ujrzysz\nWięcej mojego oblicza, jeżeli\nW szale na bliskich porywać się myślisz.\nOdchodzi.\nPrzodownik Chóru\nJak to? Czyż obie ty zgładzić zamyślasz?\nKreon\nNiewinna ujdzie; słusznie mnie strofujesz.\nPrzodownik Chóru\nA jakiż tamtej gotujesz ty koniec?\nKreon\nGdzieś na bezludnym zamknę ją pustkowiu,\n27\nW skalistym lochu zostawię żyjącą,\nStrawy przydając jej tyle, by kaźnię\nPozbawić grozy i klątwy nie ściągać;\nA tam jej Hades, którego jedynie\nZ bogów uwielbia, może da zbawienie –\nLub pozna wreszcie, jeśli marnie zginie,\nŻe próżną służbą czcić Hadesu cienie.\nOdchodzi do pałacu.\n[Stasimon III]\nChór\nMiłości, któż się wyrwie z twych obierzy!\nMiłości, która runiesz na ofiary,\nW gładkich dziew licach gdy rozniecisz czary.\nKroczysz po morzu i wśród chat pasterzy,\nNi bóg nie ujdzie przed twoim nawałem,\nAni śmiertelny. Kim władasz, wre szałem.\nZa twym podmuchem – do winy\nZboczy i prawy wraz człowiek;\nSpory ty szerzysz wśród jednej rodziny.\nUrok wystrzela zwycięsko spod powiek\nDziewicy, sięgnie i praw majestatu\nMoc Afrodyty, co przewodzi światu.\nPrzodownik Chóru\nA i ja nawet, chociaż wiernie służę,\nPrawie się w duszy na ukazy burzę,\nA boleść serce mi rani;\nBo straszny widok uderza me oczy:\nDo wszechchłonącej Antygona kroczy\nCiemnej hadesu przystani.\nStraż prowadzi A n t y g o n ę .\n28\n[Epeisodion IV]\nAntygona\nPatrzcie, o patrzcie, wy, ziemi tej dzieci,\nNa mnie, kroczącą w smutne śmierci cienie,\nOglądającą ostatnie promienie\nSłońca, co nigdy już mi nie zaświeci;\nBo mnie Hadesa dziś ręka śmiertelna\nDo Acherontu bladych wiedzie włości.\nAni zaznałam miłości,\nAni mi zabrzmi żadna pieśń weselna;\nAle na zimne Acherontu łoże\nCiało nieszczęsne me złożę.\nChór\nPieśni ty godna i w chwały rozkwicie\nW kraj śmierci niesiesz twe życie.\nAni cię chorób przygnębiło brzemię,\nNi miecza ostrze zwaliło na ziemię,\nLecz własnowolna, nie dobiegłszy kresu,\nŻywa w kraj stąpasz hadesu.\nAntygona\nSłyszałam niegdyś o frygijskiej Niobie,\nCórce Tantala, i jej strasznym zgonie,\nŻe skamieniała w swej"
                },
                {
                    "id": "sofokles_antygona_0014",
                    "title": "Antygona",
                    "author": "Sofokles",
                    "chunk_index": 14,
                    "similarity": 0.5538757984260696,
                    "fragment": "ziemi tej dzieci,\nNa mnie, kroczącą w smutne śmierci cienie,\nOglądającą ostatnie promienie\nSłońca, co nigdy już mi nie zaświeci;\nBo mnie Hadesa dziś ręka śmiertelna\nDo Acherontu bladych wiedzie włości.\nAni zaznałam miłości,\nAni mi zabrzmi żadna pieśń weselna;\nAle na zimne Acherontu łoże\nCiało nieszczęsne me złożę.\nChór\nPieśni ty godna i w chwały rozkwicie\nW kraj śmierci niesiesz twe życie.\nAni cię chorób przygnębiło brzemię,\nNi miecza ostrze zwaliło na ziemię,\nLecz własnowolna, nie dobiegłszy kresu,\nŻywa w kraj stąpasz hadesu.\nAntygona\nSłyszałam niegdyś o frygijskiej Niobie,\nCórce Tantala, i jej strasznym zgonie,\nŻe skamieniała w swej niemej żałobie\nI odtąd ciągle we łzach bólu tonie.\nSkała owiła ją, jak bujne bluszcze,\nA na jej szczytach śnieg miecie, deszcz pluszcze,\nRozpaczy łkaniem zroszone jej łono –\nMnie też kamienną pościel przeznaczono.\nChór\nLecz ona przecież z krwi bogów jest rodem,\nMy śmiertelnego pokolenia płodem.\nHołd jednak temu, kto choć w śmierci progu\nDorówna bogu.\nAntygona\nUrągasz biednej. Czemuż obelżywą\nMową mnie ranisz, pókim jeszcze żywą?\nMiasto i męże dzierżący te grody,\nWzywam was, zwróćcie litosne swe oczy,\nI wy, Teb gaje i dirkejskie wody,\nNa mnie, co idę ku ciemnej pomroczy,\nNie opłakana przez przyjaciół żale,\nDo niezwykłego grobowca gdzieś w skale.\n29\nO, ja nieszczęsna!\nAnim ja zmarła, ani też przy życiu;\nŚmierć mnie już trzyma w swym mroźnym spowiciu.\nChór\nW nadmiarze pychy zuchwałej\nZ tronem się Diki twe myśli i mowy\nZderzyły w locie, złamały.\nZły duch cię ściga rodowy.\nAntygona\nMowa ta głębią mego serca targa;\nDotknąłeś ojca ty sromu\nI w słowach twoich rozbrzmiała znów skarga\nNad nieszczęściami Labdakidów domu.\nStraszną ja pomnę łożnicę,\nW której syn z matką zdrożne śluby wiąże.\nNieszczęśni moi rodzice!\nKlątwą brzmienia dziś do was podążę,\nDziewiczość niosąc wam serca.\nO drogi bracie, złowrogie twe śluby\nByły początkiem pogromu i zguby;\nTyś – choć zmarły – mój morderca.\nChór\nZmarłych czcić – czcigodny czyn,\nAle godny kaźni błąd –\nŁamać prawo, walić rząd.\nTyś zginęła z własnych win.\nAntygona\nBez łez, przyjaciół, weselnego pienia\nKroczę już, biedna, ku śmiertelnej toni.\nWnet już nie ujrzę ni słońca promienia,\nNikt łzy nad moją dolą nie uroni.\nWchodzi K r e o n .\nKreon\nCzyżby kto ustał w przedzgonnych tych skargach,\nGdyby mu dano się żalić bez końca?\nBierzcie stąd dziewkę i w ciemnym ją grobie\nZawrzyjcie zaraz, jak już nakazałem.\nTam ją zostawcie samotną, by zmarła\nAlbo też żywa pędziła dni marne;\nTak wobec dziewki zostaniemy bez winy,\nA nie cierpimy, aby wśród nas żyła.\n30\nAntygona\nGrobie, ty mojej łożnico miłości,\nMieszkanie wieczne, ciemnico sklepiona!\nIdę do moich, których tylu gości\nW pozgonnych domach boska Persefona.\nZa wami idę ja, co w życia wiośnie\nZginęłam, prawie nie zaznawszy świata.\nA tuszę, że mnie tam przyjmą radośnie,\nTy, ojcze, matko, i miła dłoń brata:\nBom tu z miłosną służbą wasze ciała\nWłasną obmyła, namaściła ręką;\nŻem bratnie zwłoki uczciwie grzebała,\nTaką mnie darzą podzięką!\nMam u szlachetnych ludzi cześć i chwałę,\nLecz potępienie ze strony Kreona,\nBo on"
                },
                {
                    "id": "sofokles_antygona_0009",
                    "title": "Antygona",
                    "author": "Sofokles",
                    "chunk_index": 9,
                    "similarity": 0.5425664103927529,
                    "fragment": "ja czuję przeciw tym złoczyńcom,\nKtórzy swe grzechy chcą potem upiększać.\nAntygona\nChceszli co więcej, czyli śmierć mi zdać?\nKreon\nO nie! w tym jednym zawiera się wszystko.\nAntygona\nWięc na cóż zwlekać? Jako twoje słowa\nMierżą i oby zawsze mnie mierziły,\nTak wstrętne tobie wszystkie me postępki.\nA jednak skąd bym piękniejszą ja sławę\nUszczknęła, jako z brata pogrzebania?\nI ci tu wszyscy rzecz by pochwalili,\nGdyby im trwoga nie zawarła mowy.\nAle tyranów los ze wszech miar błogi,\nWolno im czynić, co zechcą, i mówić.\nKreon\nSama tak sądzisz pośród Kadmejczyków.\nAntygona\nI ci tak sądzą, lecz stulają wargi.\nKreon\nNie wstyd ci, jeśli od tych się wyróżniaż?\nAntygona\nCzcić swe rodzeństwo nie przynosi wstydu.\nKreon\nNie był ci bratem ten, co poległ drugi?\nAntygona\nZ jednego ojca i matki zrodzony.\nKreon\nCzemuż więc niesiesz cześć, co jemu wstrętna?\nAntygona\nZmarły nie rzuci mi skargi tej w oczy.\n18\nKreon\nJeśli na równi z nim uczcisz złoczyńcę?\nAntygona\nNie jak niewolnik, lecz jak brat on zginął.\nKreon\nOn, co pustoszył kraj, gdy tamten bronił?\nAntygona\nA jednak Hades pożąda praw równych.\nKreon\nDzielnemu równość ze złym nie przystoi.\nAntygona\nKtóż wie, czy takie wśród zmarłych są prawa?\nKreon\nWróg i po śmierci nie stanie się miłym.\nAntygona\nWspółkochać przyszłam, nie współnienawidzić.\nKreon\nJeśli chcesz kochać, kochaj i w Hadesie.\nU mnie nie będzie przewodzić kobieta.\nPrzodownik Chóru\nLecz otóż wiodą Ismenę, o panie;\nWidać jej boleść i słychać jej łkanie,\nA jakaś chmura przesłania jej oczy\nI piękną dziewki twarz mroczy.\nKreon\nO ty, co w domu przypięłaś się do mnie\nJak wąż podstępnie, żem wiedzieć wręcz nie mógł,\nIż na mą zgubę dwa wyrodki żywię –\nNuże, mów teraz, czyś była wspólniczką\nW tym pogrzebaniu, lub wyprzej się winy.\nIsmena\nWinna ja jestem, jak stwierdzi to siostra,\nI biorę na się tej zbrodni połowę.\nAntygona\nLecz sprawiedliwość przeczy twym twierdzeniom;\nAniś ty chciała, ni jać przypuściłam.\n19\nIsmena\nJednak w niedoli twojej nie omieszkam\nWziąć na się cząstkę twych cierpień i kaźni.\nAntygona\nHades i zmarli wiedzą, kto to zdziałał.\nSłowami świadczyć miłość, to nie miłość.\nIsmena\nO, nie zabraniaj mi siostro, choć w śmierci\nZ tobą się złączyć i uczcić zmarłego.\nAntygona\nNie chcę twej śmierci ani zwij twym dziełem,\nCoś nie sprawiła; mój zgon starczy bratu.\nIsmena\nLecz jakiż żywot mnie czeka bez ciebie?\nAntygona\nPytaj Kreona! Zwykłaś nań ty baczyć.\nIsmena\nPo cóż mnie dręczysz bez żadnej potrzeby?\nAntygona\nCierpię ja, że mi śmiać przyszło się z ciebie.\nIsmena\nW czym bym choć teraz ci przydać się mogła?\nAntygona\nMyśl o ratunku, ja go nie zawiszczę.\nIsmena\nO, ja nieszczęsna! Więc chcesz mnie porzucić?\nAntygona\nWybrałaś życie – ja życia ofiarą.\nIsmena\nSkąd wiesz, co na dnie słów moich się kryje?\nAntygona\nW słowach ty rady, ja szukałam w czynie.\nIsmena\nA jednak wina ta sama nas łączy.\n20\nAntygona\nBądź zdrowa, żyjesz – a moja już dusza\nW krainie śmierci... zmarłym świadczyć może.\nKreon\nZ dziewcząt się jednej teraz zwichnął rozum,\nDruga od"
                },
                {
                    "id": "sofokles_antygona_0018",
                    "title": "Antygona",
                    "author": "Sofokles",
                    "chunk_index": 18,
                    "similarity": 0.5229659906132181,
                    "fragment": "klęska roztrąci mą czelność.\nPrzodownik Chóru\nSynu Menoika, rozwagi ci trzeba.\nKreon\nCóż tedy czynić? Mów pójdę za radą.\n36\nPrzodownik Chóru\nIdź i wyprowadź dziewkę z ciemnej groty,\nA grób przygotuj dla ciała co leży.\nKreon\nRadzisz i mniemasz, że ja mam ustąpić?\nPrzodownik Chóru\nO, jak najprędzej, mój książę, bo chyżo\nKaźń bogów ludzkich pochwyci nierozum.\nKreon\nCiężkie to, ale każę milczeć sercu;\nCofnę się, trudno z koniecznością walczyć.\nPrzodownik Chóru\nIdź, sam to uczyń, nie zwalaj na innych.\nKreon\nIdę sam, zaraz; a wy, moi słudzy,\nWziąwszy topory pośpieszcie pospołem\nNa miejsce widne, gdzie nagi trup leży.\nJa, że zmieniłem me dawne zamysły,\nCom sam namotał, sam teraz rozwiążę.\nNajlepiej może działa, to do zgonu\nPraw istniejących przestrzegają zakonu.\nWychodzi w towarzystwie służby.\n[Stasimon V]\nChór\nWieloimienny, coś z Kadmosa domu\nPrzysporzył chwały dziewczynie,\nSynu ty Zeusa, pana burz i gromu!\nW italskiej ziemi twoje imię słynie,\nA i w Eleuzis, o synu Semeli,\nRoje cię sławią czcicieli.\nBakchosie, w Tebach ty dzierżysz stolicę,\nKędy Ismenos ciche wody toczy;\nSzałem twym tchnące pląsają dziewice,\nPieniem rozbrzmiewa gród smoczy.\n37\nWidnyś ty w łunie jarzących kagańców,\nGdzie Parnas szczytem dwugłowym wystrzela,\nGdzie zdrój Kastalii i swawolnych tańców\nKoryku nimfy zawodzą wesela.\nW górach nysejskiej Eubei\nW spowitej bluszczem mkniesz kniei,\nPotem z tych brzegów, gdzie bujne winnice,\nZwrócisz swe kroki ku Tebom;\nPieśni cię chwały wiodą przez ulice\nI brzmią radośnie ku niebom.\nGród ten nad wszystkie czcisz grody na świecie\nWraz z matką twoją ciężarną od gromu;\nKiedy więc brzemię nieszczęścia nas gniecie\nPełnego cierpień i sromu,\nPrzybądź z Parnasu ku naszej obronie\nLub przez wyjące mórz tonie.\nTy, co przodujesz wśród gwiazd korowodu,\nPieśniom przewodzisz wśród mroczy,\nZawitaj, synu Zeusowego rodu!\nNiechaj cię zastęp naksyjskich otoczy\nTyjad, co w szale od zmierzchu do rana\nTańczą i w tobie czczą pana.\nWchodzi P o s ł a n i e c .\n[Exodos]\nPosłaniec\nO kadma grodu, domu Amfiona\nMieszkańcy! Życia człowieka nie śmiałbym\nAni wysławiać, ni ganić przenigdy:\nBo los podnosi i los znów pogrąża\nBez przerwy w szczęście ludzi i w nieszczęścia,\nA nikt przyszłości wywróżyć niezdolny.\nTak Kreon zdawał się godnym podziwu,\nOn, co wyzwolił tę ziemię od wrogów\nI jako władca jedyny nad krajem\nRządził, potomstwem ciesząc się kwitnącym.\nA dziś to wszystko – stracone. Bo radość\nJeśli w człowieku przygaśnie, to trzymam,\nŻe on nie żyje, lecz żywym jest trupem.\n38\nGromadź bogactwa do woli w twym domu,\nŚwieć jako władca na zewnątrz: gdy cieszyć\nTym się nie można, to reszty tych skarbów\nJa bym nie nabył za dymu cień marny.\nPrzodownik Chóru\nJakąż ty znowu wieść niesiesz złą księciu?\nPosłaniec\nSkończyli... Śmierci ich winni, co żyją.\nPrzodownik Chóru\nKtóż to mordercą, któż poległ? O, rzeknij!\nPosłaniec\nHaimon nie żyje, we własnej krwi broczy.\nPrzodownik Chóru\nZ ojca czy z własnej zginąłże on ręki?\nPosłaniec\nW gniewie na ojca mordy sam się zabił.\nPrzodownik Chóru\nWróżbito, jakżeś czyn trafnie określił!\nPosłaniec\nW tym rzeczy stanie dalszej trza narady.\nPrzodownik Chóru\nLecz oto"
                }
                ]

                
                Niech cytat bedzie dluzszy zawierajacy kontekst sceny, kiedy dowiadujemy sie o smierci itp.
                
            """
        )
    )