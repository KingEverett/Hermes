// Polyfill TextEncoder/TextDecoder for MSW in Jest
// This must be in a .js file that runs before any imports
const { TextEncoder, TextDecoder } = require('util');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
