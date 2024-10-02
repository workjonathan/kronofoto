const path = require("path")
const MiniCssExtractPlugin = require("mini-css-extract-plugin")

module.exports = [
    {
        entry: "./kronofoto/static/assets/js/photosphere.js",
        devtool: process.env.NODE_ENV === "production" ? false : "eval",
        output: {
            filename: "photosphere.js",
            globalObject: "this",
            library: {
                type: "module",
            },
            path: path.resolve(
                __dirname,
                "./kronofoto/fortepan_us/kronofoto/static/kronofoto/js",
            ),
        },
        experiments: {
            outputModule: true,
        },
    },
    {
        entry: "./kronofoto/static/assets/js/main-dev.js",
        devtool: process.env.NODE_ENV === "production" ? false : "eval",
        output: {
            filename: "main.js",
            path: path.resolve(
                __dirname,
                "./kronofoto/fortepan_us/kronofoto/static/kronofoto/js",
            ),
        },
    },
    {
        entry: "./kronofoto/static/assets/js/kronofoto-dev.js",
        devtool: process.env.NODE_ENV === "production" ? false : "eval",
        output: {
            filename: "kronofoto.js",
            path: path.resolve(__dirname, "./kronofoto/fortepan_us/kronofoto/static"),
        },
    },
    {
        entry: "./kronofoto/static/assets/js/kronofoto-dev.js",
        output: {
            filename: "kronofoto.js",
            path: path.resolve(
                __dirname,
                "./kronofoto/fortepan_us/kronofoto/static/assets/js",
            ),
        },
    },
    {
        entry: "./kronofoto/static/assets/scss/index.scss",
        devtool: process.env.NODE_ENV === "production" ? false : "source-map",
        output: {
            path: path.resolve(
                __dirname,
                "kronofoto/fortepan_us/kronofoto/static/kronofoto/css",
            ),
        },
        optimization: {
            minimize: false,
        },
        module: {
            rules: [
                {
                    test: /\.(scss|css|sass)$/,
                    use: [
                        MiniCssExtractPlugin.loader,
                        {
                            loader: "css-loader",
                            options: {
                                url: false,
                                sourceMap: process.env.NODE_ENV === "production",
                            },
                        },
                        {
                            loader: "sass-loader",
                            options: {
                                sourceMap: process.env.NODE_ENV === "production",
                            },
                        },
                    ],
                },
            ],
        },
        plugins: [
            new MiniCssExtractPlugin({
                filename: "index.css",
            }),
        ],
    },
    {
        entry: "./kronofoto/static/assets/scss/exhibit.scss",
        devtool: process.env.NODE_ENV === "production" ? false : "source-map",
        output: {
            path: path.resolve(
                __dirname,
                "kronofoto/fortepan_us/kronofoto/static/kronofoto/css",
            ),
        },
        optimization: {
            minimize: false,
        },
        module: {
            rules: [
                {
                    test: /\.(scss|css|sass)$/,
                    use: [
                        MiniCssExtractPlugin.loader,
                        {
                            loader: "css-loader",
                            options: {
                                url: false,
                                sourceMap: process.env.NODE_ENV === "production",
                            },
                        },
                        {
                            loader: "sass-loader",
                            options: {
                                sourceMap: process.env.NODE_ENV === "production",
                            },
                        },
                    ],
                },
            ],
        },
        plugins: [
            new MiniCssExtractPlugin({
                filename: "exhibit.css",
            }),
        ],
    },
]
