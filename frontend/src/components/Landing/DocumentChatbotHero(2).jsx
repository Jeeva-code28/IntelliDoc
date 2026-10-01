import React from "react";
import hero1 from "../../assets/hero1.png";

const colors = {
  background: "#070C18",
  navy: "#122D59",
  blue: "#295D7A",
  blue2: "#23609E",
  blueBright: "#095DD0",
  blueLight: "#348BCE",
  blueSoft: "#559CE4",
  blueDeep: "#023C91",
  orange: "#DD541B",
  orangeDark: "#B25224",
  orangeLight: "#F49662",
  orangeDeep: "#B13D0F",
  orangeBright: "#C63C07",
  white: "#F0EFF0",
  muted: "#A9A7A8",
  brown: "#57230C",
  peach: "#F7C9AE",
  slate: "#475E74",
};

export default function DocumentChatbotHero() {
  return (
    <div style={styles.page}>
      {/* Navigation */}
      <header style={styles.navbar}>
        <div style={styles.logo}>
          <span style={styles.logoMark}>D</span>
          <span>DocuBot</span>
        </div>

        <nav style={styles.navLinks}>
          <button style={{ ...styles.navButton, ...styles.activeNav }}>
            Home
          </button>
          <button style={styles.navButton}>About Us</button>
          <button style={styles.navButton}>Contact</button>
          <button style={styles.signupButton}>Sign Up</button>
        </nav>
      </header>

      {/* Hero */}
      <main style={styles.hero}>
        <section style={styles.heroContent}>
          <div style={styles.badge}>
            <span style={styles.badgeDot} />
            AI-Powered Document Assistant
          </div>

          <h1 style={styles.title}>
            Chat with your
            <span style={styles.titleAccent}> Documents.</span>
          </h1>

          <p style={styles.description}>
            Upload your documents and get instant answers with an intelligent
            document chatbot. Search, understand, and interact with your files
            through natural conversations.
          </p>

          <div style={styles.actions}>
            <button style={styles.primaryButton}>Get Started</button>
            <button style={styles.secondaryButton}>Learn More</button>
          </div>

          <div style={styles.features}>
            <div style={styles.feature}>
              <span style={styles.featureIcon}>✦</span>
              <div>
                <strong style={styles.featureTitle}>Smart Answers</strong>
                <span style={styles.featureText}>
                  Ask questions in natural language
                </span>
              </div>
            </div>

            <div style={styles.feature}>
              <span style={styles.featureIcon}>▣</span>
              <div>
                <strong style={styles.featureTitle}>Document Based</strong>
                <span style={styles.featureText}>
                  Answers grounded in your files
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Right-side image */}
        <section style={styles.visual}>
          <div style={styles.glow} />
          <div style={styles.imageFrame}>
            <img
              src={hero1}
              alt="Document chatbot illustration"
              style={styles.image}
            />
          </div>
        </section>
      </main>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    width: "100%",
    boxSizing: "border-box",
    overflow: "hidden",
    background: colors.background,
    color: colors.white,
    fontFamily:
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },

  navbar: {
    height: "82px",
    width: "100%",
    boxSizing: "border-box",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 7vw",
    borderBottom: `1px solid ${colors.navy}`,
    background: colors.background,
    position: "relative",
    zIndex: 10,
  },

  logo: {
    display: "flex",
    alignItems: "center",
    gap: "11px",
    fontSize: "22px",
    fontWeight: 800,
    letterSpacing: "-0.5px",
  },

  logoMark: {
    width: "38px",
    height: "38px",
    borderRadius: "11px",
    display: "grid",
    placeItems: "center",
    background: colors.orange,
    color: colors.white,
    fontSize: "20px",
    boxShadow: `0 8px 28px ${colors.brown}`,
  },

  navLinks: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },

  navButton: {
    border: "none",
    background: "transparent",
    color: colors.muted,
    padding: "11px 17px",
    borderRadius: "9px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },

  activeNav: {
    color: colors.white,
    background: colors.navy,
  },

  signupButton: {
    border: `1px solid ${colors.orange}`,
    background: colors.orange,
    color: colors.white,
    padding: "11px 20px",
    borderRadius: "9px",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
    marginLeft: "8px",
  },

  hero: {
    minHeight: "calc(100vh - 82px)",
    width: "100%",
    boxSizing: "border-box",
    display: "grid",
    gridTemplateColumns: "0.9fr 1.1fr",
    alignItems: "center",
    gap: "20px",
    padding: "55px 6vw 65px",
    position: "relative",
  },

  heroContent: {
    maxWidth: "650px",
    position: "relative",
    zIndex: 2,
  },

  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "9px",
    padding: "8px 13px",
    borderRadius: "999px",
    background: colors.navy,
    border: `1px solid ${colors.blueDeep}`,
    color: colors.blueSoft,
    fontSize: "12px",
    fontWeight: 700,
    letterSpacing: "0.3px",
    marginBottom: "25px",
  },

  badgeDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: colors.orange,
    boxShadow: `0 0 12px ${colors.orange}`,
  },

  title: {
    margin: 0,
    fontSize: "clamp(48px, 6vw, 82px)",
    lineHeight: 0.98,
    letterSpacing: "-4px",
    fontWeight: 850,
  },

  titleAccent: {
    display: "block",
    color: colors.orange,
  },

  description: {
    maxWidth: "570px",
    margin: "28px 0 0",
    color: colors.muted,
    fontSize: "17px",
    lineHeight: 1.75,
  },

  actions: {
    display: "flex",
    gap: "13px",
    marginTop: "32px",
  },

  primaryButton: {
    border: `1px solid ${colors.orange}`,
    background: colors.orange,
    color: colors.white,
    padding: "14px 24px",
    borderRadius: "10px",
    fontSize: "14px",
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: `0 12px 30px ${colors.brown}`,
  },

  secondaryButton: {
    border: `1px solid ${colors.blue2}`,
    background: colors.navy,
    color: colors.white,
    padding: "14px 24px",
    borderRadius: "10px",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
  },

  features: {
    display: "flex",
    flexWrap: "wrap",
    gap: "25px",
    marginTop: "48px",
  },

  feature: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    minWidth: "210px",
  },

  featureIcon: {
    width: "36px",
    height: "36px",
    display: "grid",
    placeItems: "center",
    borderRadius: "10px",
    background: colors.navy,
    color: colors.orangeLight,
    border: `1px solid ${colors.blueDeep}`,
  },

  featureTitle: {
    display: "block",
    color: colors.white,
    fontSize: "13px",
    marginBottom: "3px",
  },

  featureText: {
    display: "block",
    color: colors.slate,
    fontSize: "11px",
  },

  visual: {
    minHeight: "560px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },

  glow: {
    position: "absolute",
    width: "510px",
    height: "510px",
    borderRadius: "50%",
    background: colors.navy,
    filter: "blur(70px)",
    opacity: 0.7,
  },

  imageFrame: {
    width: "100%",
    maxWidth: "780px",
    position: "relative",
    zIndex: 1,
    borderRadius: "24px",
    overflow: "hidden",
    border: `1px solid ${colors.navy}`,
    boxShadow: `0 28px 80px ${colors.background}`,
  },

  image: {
    display: "block",
    width: "100%",
    height: "auto",
    objectFit: "contain",
  },
};
