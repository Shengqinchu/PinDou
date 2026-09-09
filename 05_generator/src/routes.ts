import type { RouteRecordRaw } from 'vue-router';
export const generatorRoutes:RouteRecordRaw[]=[
 {path:'upload',redirect:'/tools'},
 {path:'',name:'tools-upload',component:()=>import('./views/UploadPage.vue')},
 {path:'loading',name:'tools-loading',component:()=>import('./views/LoadingPage.vue')},
 {path:'result/:id',name:'tools-result',component:()=>import('./views/ResultPage.vue')},
 {path:'editor/:id',name:'tools-editor',component:()=>import('./views/EditorPage.vue'),meta:{toolEditor:true}},
 {path:'works',name:'tools-works',component:()=>import('./views/WorksPage.vue')},
 {path:'tutorial',name:'tools-tutorial',component:()=>import('./views/TutorialPage.vue')},
 {path:'login',name:'tools-login',redirect:'/account?intent=login&return_to=%2Ftools'},
];
