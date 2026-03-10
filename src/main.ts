import process from 'node:process';
import {createHealth} from '@husqvarna/healthz';
import {pinoHttpDefaultOptions, startMetricsCollection} from '@husqvarna/logging';
import express from 'express';
import {pinoHttp} from 'pino-http';
import compression from 'compression';

const port = Number(process.env.PORT ?? 4001);

const logger = pinoHttp(pinoHttpDefaultOptions({
  appInsightsConnectionString: process.env.APPLICATIONINSIGHTS_CONNECTION_STRING,
}));

export const app = express();
app.disable('x-powered-by');
app.use(logger);
app.use(compression());
app.use(createHealth());

app.get('/', (request, response) => {
  response.send('Hello World!');
});

export const server = app.listen(port, () => {
  logger.logger.info(`🚀 Server ready at http://localhost:${port}`);
});

await startMetricsCollection({logger: logger.logger});

