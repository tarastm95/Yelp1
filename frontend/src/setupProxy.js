// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // 1) Проксі для вашого Django-бекенду
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  // 2) (тільки для деву!) Проксі напряму до Yelp API
  app.use(
    '/yelp-api',
    createProxyMiddleware({
      target: 'https://api.yelp.com',
      changeOrigin: true,
      pathRewrite: { '^/yelp-api': '/v3' },
    })
  );
};
