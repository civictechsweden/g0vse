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
        <meta property="og:image" content="/ulf-mozaic.jpg" />
        <meta property="og:video" content="/hejulf.mp4" />
      </Head>

      <main className="">
        <Home />
      </main>
    </div>
  );
}
