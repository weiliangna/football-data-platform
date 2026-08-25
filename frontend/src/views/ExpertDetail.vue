<template>

<div class="page">


<div v-if="loading">

加载中...

</div>



<div v-else>


<div class="header">


<h1>
{{data.user.nickname}}
</h1>


<span class="level">

{{data.user.level}}

</span>


</div>



<div class="cards">


<div class="card">

<div>
总发单
</div>

<strong>
{{data.statistics.total_orders}}
</strong>

</div>



<div class="card">

<div>
胜率
</div>

<strong>
{{data.statistics.win_rate}}%
</strong>

</div>




<div class="card">

<div>
累计盈利
</div>

<strong>

¥{{data.statistics.profit}}

</strong>

</div>



</div>




<div class="panel">


<h2>
最近7场
</h2>


<div class="history7">


<span

v-for="(item,index) in data.recent7"

:key="index"

:class="item"

>

{{item}}

</span>


</div>


</div>





<div class="panel">


<h2>
历史推荐
</h2>



<table>


<tr>

<th>
比赛
</th>


<th>
联赛
</th>


<th>
玩法
</th>


<th>
选择
</th>


<th>
金额
</th>


<th>
结果
</th>


</tr>



<tr

v-for="item in data.orders"

:key="item.id"

>


<td>
{{item.match_name || '-'}}
</td>


<td>
{{item.league || '-'}}
</td>


<td>
{{item.play_name || item.play_type}}
</td>


<td>
{{item.selection || '-'}}
</td>


<td>
{{item.stake}}
</td>


<td>
{{item.result}}
</td>


</tr>


</table>



</div>


</div>



</div>

</template>




<script setup>


import {

ref,

onMounted

}

from "vue"



import {

useRoute

}

from "vue-router"



import axios from "axios"



const route=useRoute()



const loading=ref(true)



const data=ref({

user:{},

statistics:{},

recent7:[],

orders:[]

})





async function load(){


let platform=
route.params.platform



let id=
route.params.id



let res=await axios.get(

`/api/user/detail/${platform}/${id}`

)



if(res.data.code===200){

data.value=res.data.data

}



loading.value=false


}



onMounted(()=>{

load()

})


</script>




<style scoped>


.page{

padding:20px;

background:#f5f7fa;

min-height:100vh;

}



.header{


background:white;

padding:25px;

border-radius:12px;


display:flex;

justify-content:space-between;

}



.level{


background:#1677ff;

color:white;

padding:8px 15px;

border-radius:20px;


}



.cards{


display:flex;

gap:20px;

margin-top:20px;


}



.card{


flex:1;

background:white;

padding:25px;

border-radius:12px;

text-align:center;


}



.card strong{

font-size:30px;

display:block;

margin-top:10px;

}




.panel{


background:white;

padding:20px;

margin-top:20px;

border-radius:12px;


}



.history7 span{


padding:8px 15px;

margin-right:10px;

border-radius:20px;

background:#eee;


}



.赢{

background:#52c41a!important;

color:white;

}



.输{

background:#ff4d4f!important;

color:white;

}



.待开奖{

background:#faad14!important;

color:white;

}



table{

width:100%;

border-collapse:collapse;

}



th,td{

padding:12px;

border-bottom:1px solid #eee;

text-align:center;

}


</style>
