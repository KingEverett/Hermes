/**
 * Development proxy configuration for Create React App
 *
 * This file allows dynamic proxy configuration based on environment.
 * In Docker: proxies to 'backend:8000'
 * In local dev: proxies to 'localhost:8000'
 */

const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const target = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  app.use(
    '/api',
    createProxyMiddleware({
      target: target,
      changeOrigin: true,
      logLevel: 'debug',
    })
  );
};
