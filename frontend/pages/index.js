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
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <meta property="og:title" content="g0vse - Öppna data från regeringen.se" />
        <meta property="og:image" content="https://raw.githubusercontent.com/civictechsweden/g0vse/refs/heads/master/g0vse.png" />
      </Head>

      <main className="">
        <Home />
      </main>
    </div>
  );
}
