const path = require("path")
const MiniCssExtractPlugin = require("mini-css-extract-plugin")

module.exports = [
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
