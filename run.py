import os
import uvicorn
if __name__ == '__main__':
    port = int(os.getenv('PORT', '3000'))
    os.environ.setdefault('APP_URL', f'http://127.0.0.1:{port}')
    uvicorn.run('app:app', host='127.0.0.1', port=port, access_log=False)
