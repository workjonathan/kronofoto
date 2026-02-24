const esbuild = require("esbuild")
const path = require("path")

// Determine dev vs prod
const isProd = process.env.NODE_ENV === "production"
const isWatch = process.argv.includes("--watch")

// Base output paths
const staticOut = path.resolve(
  __dirname,
  "kronofoto/fortepan_us/kronofoto/static"
)
const assetsIn = path.resolve(__dirname, "kronofoto/static/assets")
const cssOut = path.resolve(
  __dirname,
  "./kronofoto/fortepan_us/kronofoto/static/kronofoto/css"
)

// --------------- 1) Single-file JS bundles ----------------
const singleBundles = [
  {
    entryPoints: [path.join(assetsIn, "js/photosphere.js")],
    outfile: path.join(staticOut, "kronofoto/js/photosphere.js"),
    format: "esm",
    bundle: true,
    sourcemap: !isProd,
    minify: isProd,
  },
  {
    entryPoints: [path.join(assetsIn, "js/kronofoto-dev.js")],
    outfile: path.join(staticOut, "kronofoto.js"),
    format: "iife",
    bundle: true,
    sourcemap: !isProd,
    minify: isProd,
  },
  {
    entryPoints: [path.join(assetsIn, "js/kronofoto-dev.js")],
    outfile: path.join(staticOut, "assets/js/kronofoto.js"),
    format: "iife",
    bundle: true,
    sourcemap: !isProd,
    minify: isProd,
  },
]

// --------------- 2) Main JS bundle (splitting) ----------------
const mainBundle = {
  entryPoints: [path.join(assetsIn, "js/main.js")],
  outdir: path.join(staticOut, "kronofoto/js"),
  bundle: true,
  format: "esm",
  splitting: true,         // dynamic imports become async chunks
  mainFields: ["browser", "module", "main"],
  sourcemap: !isProd,
  alias: {
    jquery: require.resolve("jquery"),
  },
  minify: isProd,
  chunkNames: "chunk-[name]-[hash]",
}

// --------------- 3) SCSS builds ----------------
const scssBuilds = [
  {
    entry: "./static/assets/scss/index.scss",
    outfile: path.join(cssOut, "index.css"),
  },
  {
    entry: "./static/assets/scss/exhibit.scss",
    outfile: path.join(cssOut, "exhibit.css"),
  },
]

// Function to build JS single bundles
async function buildSingleJS() {
  for (const b of singleBundles) {
    await esbuild.build(b)
  }
}

// Function to build main JS bundle
async function buildMainJS() {
  await esbuild.build(mainBundle)
}

// Function to build SCSS
async function buildSCSS() {
  for (const b of scssBuilds) {
    await esbuild.build({
      entryPoints: [b.entry],
      outfile: b.outfile,
      bundle: true,
      loader: { ".scss": "css" },
      external: ["*.svg", "*.png", "*.jpg", "*.gif"],
      minify: isProd,
      sourcemap: !isProd,
    })
  }
}


// Run all builds
async function runBuilds() {
  console.log(`production mode = ${isProd}`)
  const bundles = [...singleBundles, mainBundle]
  if (isWatch) {
    const contexts = await Promise.all(bundles.map(bundle => esbuild.context(bundle)))
    await Promise.all(contexts.map(ctx => ctx.watch()))
    console.log("running esbuild in watch mode")
  } else {
    await buildSingleJS()
    await buildMainJS()
  }
  // await buildSCSS()
  // gave up trying to get esbuild to compile scss
}

runBuilds().catch((err) => {
  console.error(err)
  process.exit(1)
})

