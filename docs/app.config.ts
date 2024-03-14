export default defineAppConfig({
  docus: {
    title: '🔊 Yassi',
    description: 'Yet another Samsung Soundbar integration for Home Assistant',
    image: 'https://user-images.githubusercontent.com/904724/185365452-87b7ca7b-6030-4813-a2db-5e65c785bf88.png',
    socials: {
      github: 'samuelspagl/ha_samsung_soundbar',
      nuxt: {
        label: 'Nuxt',
        icon: 'simple-icons:nuxtdotjs',
        href: 'https://nuxt.com'
      }
    },
    github: {
      dir: 'docs/content',
      branch: 'main',
      repo: 'ha_samsung_soundbar',
      owner: 'samuelspagl',
      edit: true
    },
    aside: {
      level: 0,
      collapsed: false,
      exclude: []
    },
    main: {
      padded: true,
      fluid: true
    },
    header: {
      logo: false,
      showLinkIcon: true,
      exclude: [],
      fluid: true
    }
  }
})
