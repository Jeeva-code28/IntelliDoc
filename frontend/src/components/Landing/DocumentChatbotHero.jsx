import React from "react";
import hero1 from "../../assets/hero(background_removed).png";

const palette = {
  ink: "#040710",
  navy: "#0C1424",
  blueDark: "#122D59",
  blue: "#2C6CA4",
  blueBright: "#3C87D1",
  orange: "#EB5D22",
  orangeDark: "#CB4711",
  peach: "#F49866",
  white: "#F2F1F1",
};

export default function DocumentChatbotHero() {
  return (
    <main
      className="min-h-screen overflow-hidden font-sans"
      style={{ backgroundColor: palette.ink, color: palette.white }}
    >
      {/* Navigation */}
      <header className="relative z-20 border-b border-[#2C6CA4]/30">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <a href="#" className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ backgroundColor: palette.orange }}
            >
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6"
                fill="none"
                stroke={palette.white}
                strokeWidth="2"
              >
                <path d="M6 3h8l4 4v14H6z" />
                <path d="M14 3v5h5" />
                <path d="M9 13h6M9 17h6" />
              </svg>
            </div>

            <span className="text-lg font-bold tracking-tight">
              Docu<span style={{ color: palette.orange }}>Chat</span>
            </span>
          </a>

          <div className="hidden items-center gap-9 text-sm md:flex">
            <a
              href="#home"
              className="transition hover:text-[#EB5D22]"
              style={{ color: palette.white }}
            >
              Home
            </a>
            <a
              href="#about"
              className="transition hover:text-[#EB5D22]"
              style={{ color: palette.white }}
            >
              About Us
            </a>
            <a
              href="#contact"
              className="transition hover:text-[#EB5D22]"
              style={{ color: palette.white }}
            >
              Contact
            </a>
          </div>

          <button
            type="button"
            className="rounded-full px-5 py-2.5 text-sm font-semibold transition hover:-translate-y-0.5"
            style={{
              backgroundColor: palette.orange,
              color: palette.white,
            }}
          >
            Sign Up
          </button>
        </nav>
      </header>

      {/* Hero */}
      <section id="home" className="relative">
        {/* Decorative shapes using only image colors */}
        <div
          className="pointer-events-none absolute -left-40 top-32 h-96 w-96 rounded-full blur-3xl opacity-40"
          style={{ backgroundColor: palette.blueDark }}
        />
        <div
          className="pointer-events-none absolute right-0 top-0 h-80 w-80 rounded-full blur-3xl opacity-30"
          style={{ backgroundColor: palette.blue }}
        />

        <div className="relative mx-auto grid min-h-[calc(100vh-81px)] max-w-7xl items-center gap-10 px-6 py-14 lg:grid-cols-[0.9fr_1.1fr] lg:px-10 lg:py-16">
          {/* Left content */}
          <div className="max-w-2xl">

            <h1 className="text-5xl font-black leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
              Talk to your
              <span className="block" style={{ color: palette.orange }}>
                documents.
              </span>
            </h1>

            <p
              id="about"
              className="mt-7 max-w-xl text-base leading-8 sm:text-lg"
              style={{ color: "#ADC0CF" }}
            >
              Upload your documents and ask questions in natural language.
              DocuChat uses AI to understand your files, find the information
              you need, and give clear answers without making you search through
              pages manually.
            </p>

            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <button
                type="button"
                className="rounded-xl px-6 py-3.5 font-bold transition hover:-translate-y-1"
                style={{
                  backgroundColor: palette.orange,
                  color: palette.white,
                }}
              >
                Get Started
              </button>

              <button
                type="button"
                className="rounded-xl border px-6 py-3.5 font-bold transition hover:-translate-y-1"
                style={{
                  borderColor: palette.blue,
                  backgroundColor: palette.navy,
                  color: palette.white,
                }}
              >
                Learn More
              </button>
            </div>

            {/* Project highlights */}
            <div className="mt-12 grid max-w-xl grid-cols-3 gap-3">
              {[
                ["01", "Upload", "Add your documents"],
                ["02", "Ask", "Use natural language"],
                ["03", "Understand", "Get useful answers"],
              ].map(([number, title, text]) => (
                <div
                  key={number}
                  className="rounded-2xl border p-4"
                  style={{
                    borderColor: `${palette.blue}70`,
                    backgroundColor: `${palette.navy}CC`,
                  }}
                >
                  <div
                    className="text-xs font-bold"
                    style={{ color: palette.orange }}
                  >
                    {number}
                  </div>
                  <div className="mt-2 font-bold">{title}</div>
                  <div
                    className="mt-1 text-xs leading-5"
                    style={{ color: "#ADC0CF" }}
                  >
                    {text}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right image */}
          <div className="relative flex items-center justify-center lg:justify-end">
            <div
              className="absolute h-[75%] w-[75%] rounded-full blur-3xl opacity-40"
              style={{ backgroundColor: "transparent" }}
            />

            <div
              className="relative w-full max-w-2xl overflow-hidden"
              style={{
                backgroundColor: "transparent"
              }}
            >
              <img
                src={hero1}
                alt="AI document chatbot illustration"
                className="h-auto w-full rounded-[1.5rem] object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Contact anchor */}
      <section
        id="contact"
        className="mx-auto max-w-7xl px-6 pb-10 text-center lg:px-10"
      >
        <p className="text-sm" style={{ color: "#ADC0CF" }}>
          A smarter way to interact with your documents.
        </p>
      </section>
    </main>
  );
}
