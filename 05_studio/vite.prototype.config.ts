import { mergeConfig } from 'vite';
import studio from './vite.config';
export default mergeConfig(studio,{server:{port:19679,proxy:{'/studio-api':{target:'http://127.0.0.1:19678'},'/api/v1':{target:'http://127.0.0.1:19678'}}}});
