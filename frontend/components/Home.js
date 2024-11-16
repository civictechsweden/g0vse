import Image from 'next/image';
import React, { useState } from "react";
import types from '../../types.json';

export default function Home() {
  React.useEffect(() => {
    const fetchLatestData = async () => {
      try {
        const response = await fetch("https://g0v.se/api/latest_updated.json");
        const data = await response.json();
        setLatestData(data);
      } catch (error) {
        setErrorMessage("Kunde inte ladda senaste data");
      }
    };
    fetchLatestData();
  }, []);

  const [oldLink, setOldLink] = useState("");
  const [newLink, setNewLink] = useState("");
  const [removedPrefix, setRemovedPrefix] = useState("");
  const [addedPrefix, setAddedPrefix] = useState("");
  const [middle, setMiddle] = useState("");
  const [removedSuffix, setRemovedSuffix] = useState("");
  const [addedSuffix, setAddedSuffix] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [latestData, setLatestData] = useState(null);
  const regexPrefix = /^(https?:\/\/)?(www\.)?(regeringen\.se|gov\.se)/;
  const regexSuffix = /\/$/

  const convert = async (e) => {
    const link = e.target.value;
    setOldLink(link);
    e.preventDefault();

    if (regexPrefix.test(link)) {
      const addedPrefix = "https://g0v.se";
      const removedPrefix = link.match(regexPrefix);
      var updatedLink = link.replace(regexPrefix, "");
      const removedSuffix = link.match(regexSuffix);
      updatedLink = updatedLink.replace(regexSuffix, "");

      var addedSuffix = "";

      if (updatedLink == "") {
        addedSuffix += "/api/items.json";
      }
      else if (types.some(type => updatedLink.endsWith(type))) {
        addedSuffix += ".json";
      }
      else {
        addedSuffix += ".md";
      }

      if (removedPrefix) {
        setRemovedPrefix(removedPrefix[0]);
      }

      setAddedPrefix(addedPrefix);
      setMiddle(updatedLink);
      setRemovedSuffix(removedSuffix);
      setAddedSuffix(addedSuffix);
      setNewLink(addedPrefix + updatedLink + addedSuffix);

      setErrorMessage("");
    }
    else if (!link) {
      setNewLink("");
      setErrorMessage("");
    }
    else {
      setNewLink("");
      setErrorMessage("Ogiltig länk");
    }
  };
  return (
    <main>
      <header id="converter" className="lg:p-8 grid grid-cols-1 md:grid-cols-2 gap-4 lg:px-40 md:h-100">
        <div className="mx-auto md:mr-auto m-5">
          <div className="flex items-center">
            <Image src="/logo.svg" alt="g0vse logo" className="mr-4 mt-4 mb-4" height={43.238} width={74.876} />
            <h1 className="text-8xl font-bold dark:text-white text-black font-mono">
              g0vse
            </h1>
          </div>
          <h2 className="text-2xl font-bold mt-4 dark:text-gray-50 text-gray-700">
            regeringen.se som öppna data
          </h2>
          <p className="text-xl text-gray-700 mt-4 font-light dark:text-gray-200">
            En av Sveriges viktigaste webbplatser... <br/>..äntligen tillgänglig som öppna data!
          </p>
          <p className="text-xs mt-4 font-bold dark:text-gray-200">
            OBS: g0vse har ingen koppling med regeringen eller Regeringskansliet.
          </p>
        </div>
        <form
          className="rounded-lg shadow-xl flex flex-col px-8 py-8 bg-white dark:bg-blue-500"
        >
          <h1 className="text-2xl font-bold dark:text-gray-50">
            Konvertera en länk
          </h1>
          <div className="text-left">
            <p className="mb-2 text-xs text-gray-500">Ange en länk från regeringen.se eller gov.se</p>
          </div>
          <label htmlFor="oldLink" className="text-500 text-xs font-light my-1 1ark:text-gray-50">
            Länk<span className="text-red-500 dark:text-gray-50">*</span>
          </label>
          <input
            type="text"
            value={oldLink}
            onChange={(e) => {
              convert(e);
            }}
            name="oldLink" className={`bg-transparent border-b py-2 pl-4 rounded-md ring-1 ${!oldLink ? "ring-black" : !newLink ? "ring-red-500" : "ring-green-500"} outline-none`}
          />
          <p className="text-xs mt-1 dark:text-gray-200">
            {latestData ? "Antal tillgängliga sidor: " + latestData.items + "." : ""}
            {latestData ? " Senast uppdaterat: " + latestData.latest_updated + "." : ""}
          </p>
          {newLink ? (
            <>
              <div className="mt-3 flex flex-row items-center justify-start">
                <a className="underline" href={newLink} target="_blank" rel="noreferrer">{newLink.replace("https://", "")}</a>
              </div>
              <div className="mt-3 text-xs">
                <span className="text-red-500 line-through">{removedPrefix.replace("https://", "")}</span>
                <span className="text-green-500">{addedPrefix.replace("https://", "")}</span>
                <span className="text-black-500">{middle}</span>
                <span className="text-red-500 line-through">{removedSuffix}</span>
                <span className="text-green-500">{addedSuffix}</span>
              </div>
              <div className="text-left">
                <p className="mt-2 text-xs text-gray-500">Observera att de genererade länkarna kan vara otillförlitliga. Nedan finner du en lista med bekräftade API-rutter.</p>
              </div>
            </>
          ) : (
          <div className="mt-3 flex flex-row items-center justify-start">
            <div className="text-red-500 dark:text-gray-50">
              {errorMessage}
            </div>
          </div>
          )}
        </form>
      </header>
      <section>
        <h1 className="text-4xl font-bold text-center gradient-text text-gray-700 mx-10 mt-5 mb-0">
          Vad är g0vse?
        </h1>
        <div className="mx-auto my-5 max-w-5xl">
          <p className="m-5 text-xl text-gray-700 font-light dark:text-gray-200">
            g0vse som samlar in viktig information och data från regeringens webbplats och gör den tillgänglig som öppen och strukturerad data.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Regeringen publicerar dagligen information som är av stor betydelse för oss alla. Det handlar om allt från beslut och statliga utredningar till propositioner och öppna remissförfaranden. Denna information används av tusentals tjänstepersoner, politiker, journalister, forskare, lobbyister och engagerade medborgare. Tyvärr är den ofta svår att hitta och integrera i andra digitala tjänster.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Projektet g0vse har som mål att sänka trösklarna för återanvändning av offentlig information och dokument från regeringen, så att de blir enklare att hitta, använda och sprida.
          </p>
        </div>
      </section>
      <section>
        <h1 className="text-4xl font-bold text-center gradient-text text-gray-700 mx-10 mt-5 mb-0">
          Hur kommer jag åt datat?
        </h1>
        <div className="mx-auto my-5 max-w-5xl">
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Det finns flera API-anrop för att hämta listor för specifika typer av dokument eller sidor:
          </p>
          <ul className="m-5 ml-10 list-disc list-inside">
          {types.map((type, index) => (
              <li key={index} className="mb-1 text-lg text-gray-700">
                <a href={"https://g0v.se/" + type + ".json"} target="_blank" rel="noreferrer" className="underline text-black-700">
                  {"/" + type + ".json"}
                </a>
              </li>
            ))}
          </ul>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Utöver det finns det tre extra anrop:
          </p>
          <ul className="m-5 ml-10 list-disc list-inside">
            <li className="mb-1 text-lg text-gray-700">
              <a href={"https://g0v.se/api/items.json"} target="_blank" rel="noreferrer" className="underline text-black-700">{"/api/items.json"}</a> hämtar alla sidor (OBS: stor fil)
            </li>
            <li className="mb-1 text-lg text-gray-700">
              <a href={"https://g0v.se/api/codes.json"} target="_blank" rel="noreferrer" className="underline text-black-700">{"/api/codes.json"}</a> hämtar alla kategorikoder
            </li>
            <li className="mb-1 text-lg text-gray-700">
              <a href={"https://g0v.se/api/latest_updated.json"} target="_blank" rel="noreferrer" className="underline text-black-700">{"/api/latest_updated.json"}</a> hämtar nyckelinformation om datat
            </li>
          </ul>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            För varje kategori får man en lista av alla sidor med följande metadata:
          </p>
          <ul className="m-5 ml-10 list-disc list-inside">
            <li className="mb-1 text-lg text-gray-700">
              Rubrik
            </li>
            <li className="mb-1 text-lg text-gray-700">
              Publicerings- och uppdateringsdatum
            </li>
            <li className="mb-1 text-lg text-gray-700">
              Typ av innehåll och kategorier enligt ovannämnda kategorikoder
            </li>
            <li className="mb-1 text-lg text-gray-700">
              Avsändare
            </li>
            <li className="mb-1 text-lg text-gray-700">
              Beteckningsnummer
            </li>
            <li className="mb-1 text-lg text-gray-700">
              Genvägar och bilagor
            </li>
          </ul>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Till slut är det också möjligt att komma åt många enskilda sidors text i Markdown-format genom att ersätta domännamnet med g0v.se och det slutliga &quot;/&quot; med &quot;.md&quot;. <a href="#converter" className="underline text-black-700">Fältet</a> vid sidans topp kan hjälpa att utforma den nya adressen rätt.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Allt som går att hämta finns på <a href="https://github.com/civictechsweden/g0vse/tree/data" target="_blank" rel="noreferrer" className="underline text-black-700">Github</a>.
          </p>
        </div>
      </section>
      <section>
        <h1 className="text-4xl font-bold text-center gradient-text text-gray-700 mx-10 mt-5 mb-0">
          Varför inte vänta för Regeringskansliets officiella API?
        </h1>
        <div className="mx-auto my-5 max-w-5xl">
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Tyvärr har många efterfrågat öppna data i många år, inklusive aktörer som Riksdagen. Men Regeringskansliet har hittills inte prioriterat det och det finns inga signaler för officiella öppna data från dem under de kommande åren.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            <a href="https://github.com/civictechsweden/g0vse" target="_blank" rel="noreferrer" className="underline text-black-700">Projektets källkod</a> är helt öppen så om de vill komma igång snabbt är de välkomna att återanvända den.
          </p>
        </div>
      </section>
      <section>
        <h1 className="text-4xl font-bold text-center gradient-text text-gray-700 mx-10 mt-5 mb-0">
          Varför heter projektet g0vse?
        </h1>
        <div className="mx-auto my-5 max-w-5xl">
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Efter solrosrevolutionen i Taiwan skapade digitala aktivister <a href="https://www.taiwan-panorama.com/en/Articles/Details?Guid=736828dd-9df4-48fe-9383-71a5353cf4b7" target="_blank" rel="noreferrer" className="underline text-black-700">g0v</a> (uttalas &quot;gov-zero&quot;) och mottot <a href="https://www.wired.com/story/taiwan-sunflower-revolution-audrey-tang-g0v/" target="_blank" rel="noreferrer" className="underline text-black-700">&quot;fork the government&quot;</a>. För att förbättra regeringens dåligt utformade digitala tjänster utvecklade de bättre och mer transparenta alternativ och hostade dem på g0v.tw-domänen. För att byta från de officiella webbplatserna (som slutar på gov.tw) till gräsrotsalternativen (som slutar på g0v.tw) behövde medborgarna bara ändra en bokstav i webbplatsens URL.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            I Sverige är situationen liknande. Trots vissa insatser har offentlig sektor svårt att gå från reaktiv transparens (analog offentlighetsprincip) till proaktiv transparens med öppna data. Regeringskansliet publicerar allt mer viktig information på regeringen.se, men utan API:er. Detta tvingar civilsamhället, journalister och myndigheter till manuellt arbete för att komma åt datan. Webbscrapers används ibland som lösning, men de är ofta komplexa och opålitliga.
          </p>
          <p className="m-5 text-xl text-gray-700 mt-0 font-light dark:text-gray-200">
            Målet med g0vse är att bygga den bästa webscrapern och göra data tillgänglig för alla att återanvända. Förhoppningsvis blir det ännu bättre i framtiden tack vare kollaborativt arbete. Data hämtas idag på ett respektfullt sätt utan att sätta press på regeringens webbplats och bör så småningom minska pressen på den genom att ta bort behovet för andras webscrapers.
          </p>
        </div>
      </section>
      <section>
        <div className="mx-auto my-5 max-w-5xl text-center">
          <p className="m-5 text-m text-gray-700 mt-0 font-light dark:text-gray-200 italic">
            Denna webbsida togs fram av <a className="underline" href="https://www.linkedin.com/in/pierremesure/" target="_blank" rel="noreferrer">Pierre Mesure</a> och publiceras som <a className="underline" href="https://github.com/civictechsweden/g0vse" target="_blank" rel="noreferrer">öppen källkod</a> ❤️ (AGPLv3).
          </p>
        </div>
      </section>
    </main>
  );
}
