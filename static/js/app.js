(function(){var s=localStorage.getItem('en-theme');if(s)document.documentElement.dataset.theme=s;
var t=document.getElementById('themeToggle');if(t)t.addEventListener('click',function(){var n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('en-theme',n)});})();
