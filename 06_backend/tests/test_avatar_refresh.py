"""Avatar URLs must identify their image, including across the two account clients."""
import io
from PIL import Image
from test_api import api_client,auth_headers

def test_replacing_avatar_changes_url_and_requires_authentication(api_client):
    client,_=api_client
    headers=auth_headers(client,consent=False)
    def upload(color):
        output=io.BytesIO();Image.new('RGB',(200,120),color).save(output,format='PNG')
        response=client.post('/api/user/avatar',headers=headers,files={'image':('avatar.png',output.getvalue(),'image/png')})
        assert response.status_code==200
        return response.json()
    first=upload('red');second=upload('blue');repeated=upload('blue')
    assert first['avatar_url']!=second['avatar_url']==repeated['avatar_url']
    assert second['user']['user_id']==first['user']['user_id']
    assert client.get('/api/user/profile',headers=headers).json()['avatar']==second['avatar_url']
    assert client.post('/api/user/avatar',files={'image':('avatar.png',b'invalid','image/png')}).status_code==401
