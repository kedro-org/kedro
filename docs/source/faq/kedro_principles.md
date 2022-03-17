# Kedro Principles

After a long discussion, we wrote this set of principles to summarise our development philosophy and to guide us through future decisions about Kedro.

### 1. Modularity at the core ️📦
Modularity allows for easy construction, flexible arrangements and reusability of components, resulting in an extensible and customisable system. Kedro is built around the idea of enabling modular data engineering and data science code. To make this possible, we take this as our core tenet and make sure Kedro’s own components are modular and independent of each other as much as possible. Each component has clearly defined responsibilities and narrow interfaces. We aim to make most of our components highly decoupled from each other and ensure they can be used on their own.

### 2. Grow beginners into experts 🌱
Every user is on a learning journey and Kedro aims to be the perfect vehicle for such an adventure. We want Kedro to be loved by users across all different levels of experience. Kedro should be your companion as a beginner, taking your first steps into building data products, or as an expert user, well-seasoned in taking machine-learning models into production.

### 3. User empathy without unfounded assumptions 🤝
Kedro is designed with the user in mind, but makes no guesses about what the user has in mind. We strive to understand our users without claiming we are one with them. Our users trust us with their time to learn our API and we should make sure we spend their time wisely. All our assumptions should be grounded on extensive experience and hard data.

### 4. Simplicity means bare necessities 🍞
We believe that simplicity is “attained not when there is no longer anything to add, but when there is no longer anything to take away”, very much like Antoine de Saint-Exupéry’s definition of perfection. Simplicity is hard to achieve, but once achieved it is easy to understand and rely on. In our pursuit of simplicity at Kedro we start by defining it as something composed of small number of parts, with small number of features or functional branches and having very little optionality. Simple things are easy, robust, reliable and loved by everyone. They can be used in countless ways on their own or effortlessly become a part of a more complex system since they are modular by nature.

### 5. There should be one obvious way of doing things 🎯
Inspired by The Zen of Python, we recommend certain ways of accomplishing tasks. We do this because it allows users to focus on their original problem rather than deal with accidental complexity. That doesn’t mean that it will be impossible to do things using a different way; but, as one becomes more accustomed to Kedro, it will become apparent that there is a preferred way of doing things. Kedro is an opinionated framework, and this is built into its design.

### 6. A sprinkle of magic is better than a spoonful of it ✨
The declarative nature of Kedro introduces some magic by hiding the imperative implementation details. However, we recognise that this departure from Python’s preference for explicit solutions can be taken too far and quickly spiral into “dark magic”. Dark magic introduces confusion for the users and can make it easy for them to get lost in their own project. That’s why we have a strong preference for common sense over dark magic and making things obvious rather than clever. Nevertheless, magic is sometimes justified if it simplifies how things work. We promise to use it sparingly and only for good.

### 7. Lean process and lean product 👟
Kedro started as a small framework which tackles big problems in the delivery of data science projects from inception to production. We fully subscribe to the principles of lean software development and do our best to eliminate waste as much as possible. We favour small incremental changes over big bang deliveries of functionality and in general we strive to achieve more with less.
