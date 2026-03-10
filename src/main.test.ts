import type {Server} from 'node:http';
import {
  afterAll, afterEach, beforeAll, describe, expect, test, vi,
} from 'vitest';
import supertest from 'supertest';

describe('createHealth', () => {
  let server: Server;
  let app: Express.Application;

  beforeAll(async () => {
    const main = await import('./main.js');
    server = main.server;
    app = main.app;
  });

  afterAll(async () => {
    server.close();
  });

  test('returns 200 for /h', async () => {
    const response = await supertest(server).get('/');
    expect(response.text).toStrictEqual('Hello World!');
  });

  test('returns 200 for /healthz', async () => {
    const response = await supertest(server).get('/healthz');
    expect(response.body).toMatchObject({status: 'ok'});
  });
});
