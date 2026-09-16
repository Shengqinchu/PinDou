<script setup lang="ts">
import {onLoad} from '@dcloudio/uni-app';
import {navigateStudio} from '../../utils/studio-navigation';
import {workspaceUrl} from '../../utils/studio-workspace-router';
onLoad(query=>navigateStudio(workspaceUrl('pages/studio/manage-finance',query||{})));
</script>
<template><view/></template>
