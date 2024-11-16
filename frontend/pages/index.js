import Head from "next/head";
import Home from "../components/Home";

export default function Index() {
  return (
    <div className="">
      <Head>
        <title>g0vse</title>
        <meta
          name="description"
          content="Öppna data från regeringen.se"
        />
        <link rel="icon" href="/favicon.ico" />
        <meta property="og:title" content="g0vse - Öppna data från regeringen.se" />
        <meta property="og:image" content="https://raw.githubusercontent.com/civictechsweden/g0vse/refs/heads/master/g0vse.png" />
      </Head>

      <main className="">
        <Home />
      </main>
    </div>
  );
}
